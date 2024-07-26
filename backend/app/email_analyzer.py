import asyncio
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import csv
from datetime import datetime
import dateutil.parser
import base64
import re
import logging
from openai import AsyncOpenAI
import os
from collections import defaultdict
import threading
from flask import current_app
import aiohttp
import cachetools

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for storing processed email data
email_cache = cachetools.TTLCache(maxsize=1000, ttl=3600)

class ProgressTracker:
    def __init__(self):
        self.total_emails = 0
        self.processed_emails = 0
        self.total_threads = 0
        self.processed_threads = 0
        self.total_companies = 0
        self.analyzed_companies = 0
        self.status = "Not started"
        self.num_startups = 0
        self.current_step = "Initializing"
        self.lock = threading.Lock()

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)
            current_app.logger.info(f"Progress update: {self.__dict__}")

    def get_state(self):
        with self.lock:
            return {
                'status': self.status,
                'total_emails': self.total_emails,
                'processed_emails': self.processed_emails,
                'total_companies': self.total_companies,
                'analyzed_companies': self.analyzed_companies,
                'num_startups': self.num_startups,
                'current_step': self.current_step
            }

progress_tracker = ProgressTracker()

# Analyzes email threads to identify potential startup companies
async def analyze_emails(credentials):
    global progress_tracker
    current_app.logger.info("Starting email analysis")
    progress_tracker.update(status="Fetching emails")
    
    service = build('gmail', 'v1', credentials=credentials)
    
    companies = defaultdict(lambda: {"threads": [], "interactions": 0})
    page_token = None
    processed_emails = 0
    max_emails = 15  # Limit to 15 emails
    processed_threads = 0

    current_app.logger.info(f"Fetching a maximum of {max_emails} emails")

    while True:
        results = service.users().threads().list(userId='me', maxResults=5, pageToken=page_token).execute()
        threads = results.get('threads', [])
        
        current_app.logger.info(f"Fetched {len(threads)} threads")
        
        for thread in threads:
            thread_data = service.users().threads().get(userId='me', id=thread['id']).execute()
            thread_emails = await asyncio.gather(*[extract_email_data(msg) for msg in thread_data['messages']])
            
            current_app.logger.info(f"Processing thread with {len(thread_emails)} emails")
            
            company_name = extract_company_name(thread_emails[0])
            if company_name:
                companies[company_name]["threads"].append(thread_emails)
                companies[company_name]["interactions"] += len(thread_emails)
                current_app.logger.info(f"Added {len(thread_emails)} emails to company: {company_name}")
            
            processed_emails += len(thread_emails)
            processed_threads += 1
            progress_tracker.update(
                total_emails=max_emails,
                processed_emails=min(processed_emails, max_emails),
                total_threads=processed_threads,
                status=f"Processed {processed_threads} threads, {min(processed_emails, max_emails)}/{max_emails} emails"
            )

            if processed_emails >= max_emails:
                break

        if processed_emails >= max_emails or 'nextPageToken' not in results:
            break
        page_token = results['nextPageToken']

    current_app.logger.info(f"Processed {processed_threads} threads, {processed_emails} emails. Found {len(companies)} companies")
    progress_tracker.update(total_companies=len(companies), status="Analyzing companies", analyzed_companies=0)
    startup_companies = await analyze_companies(companies)
    progress_tracker.update(status="Generating CSV", num_startups=len(startup_companies))
    csv_path = generate_csv(startup_companies)
    progress_tracker.update(status="Completed")
    return len(startup_companies), csv_path

# Extracts relevant data from an email message
async def extract_email_data(msg):
    msg_id = msg.get('id', 'Unknown')
    if msg_id in email_cache:
        current_app.logger.info(f"Retrieved email {msg_id} from cache")
        return email_cache[msg_id]

    current_app.logger.info(f"Extracting data for email {msg_id}")

    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '')
    date = next((header['value'] for header in headers if header['name'].lower() == 'date'), '')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')

    body = await get_email_body(msg)
    body = body[:5000]  # Limit to first 5000 characters

    parsed_date = parse_date(date)

    email_data = {
        'date': parsed_date,
        'subject': subject,
        'sender': sender,
        'email': extract_email_address(sender),
        'body': body
    }

    email_cache[msg_id] = email_data
    current_app.logger.info(f"Extracted and cached data for email {msg_id}")
    return email_data

# Parses a date string into a standard format
def parse_date(date_string):
    try:
        dt = dateutil.parser.parse(date_string)
        return dt.strftime("%Y-%m-%d")
    except:
        return date_string  # Return original string if parsing fails

# Extracts the company name from an email address
def extract_company_name(email_data):
    domain = email_data['email'].split('@')[1]
    if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
        return domain
    return None

# Analyzes companies to determine if they are startups
async def analyze_companies(companies):
    global progress_tracker
    company_summaries = []
    for i, (company_name, data) in enumerate(companies.items(), 1):
        current_app.logger.info(f"Analyzing company: {company_name}")
        summary = f"Company: {company_name}\n"
        summary += f"Interactions: {data['interactions']}\n"
        summary += "Email Threads:\n"
        for thread in data['threads'][:3]:  # Limit to 3 threads per company
            summary += "Thread:\n"
            for email in thread[:3]:  # Limit to 3 emails per thread
                summary += f"Subject: {email.get('subject', 'No subject')}\n"
                body = email.get('body', '')
                if body:
                    summary += f"Body: {body[:300]}...\n"
                else:
                    summary += "Body: No body content\n"
                summary += "\n"
        company_summaries.append(summary)
        progress_tracker.update(analyzed_companies=i, status=f"Analyzing company {i}/{len(companies)}")

    prompt = f"""
    Analyze the following email content for each company and determine if they are startups that our venture capital firm might be considering for investment. Focus primarily on the email body content, not just the subject lines.
    If it is a service we're evaluating as a tool that would be used by the firm, it's not a startup. Otherwise, consider the following as potential indicators of a startup:

    1. Discussions about funding rounds, investments, or pitching to investors
    2. If a company is sending over a deck and/or financials, it's likely a startup, but understand context to make sure it's not just a service we're considering paying for.
    3. Requests for meetings, demos, or further discussions with investors. However, if the email thread is only 1 email and it's a calendar invite, it's not a startup.
    4. Mentions of product launches, growth metrics, or market opportunities
    5. Any indication of early-stage or innovative technology

    For each company, provide a concise analysis:
    Clearly state if this is likely a startup (yes/no)
    Briefly explain your reasoning (1 sentence)
    If it's a startup, summarize what stage they seem to be at and what they're looking for

    If there's insufficient information, err on the side of No.
    If it's from fireflies.ai or affinity, it's not a startup. 
    Be thorough in your analysis.

    {' '.join(company_summaries)}
    """

    current_app.logger.info("Sending request to OpenAI for company analysis")
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant analyzing potential startup investments for a venture capital firm. Your task is to identify startups from email communications, focusing primarily on the content of the email body."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            n=1,
            temperature=0.2
        )
        ai_response = response.choices[0].message.content.strip()
        current_app.logger.info("Received response from OpenAI")
        
        startup_companies = {}
        for company_analysis in ai_response.split('\n\n'):
            lines = company_analysis.split('\n')
            if len(lines) >= 2:
                ai_company_name = ' '.join(lines[0].replace('Company:', '').strip().strip('*').split()).lower()
                is_startup = 'yes' in lines[1].strip().lower()
                current_app.logger.info(f"AI analysis for {ai_company_name}: {'Startup' if is_startup else 'Not a startup'}")
                if is_startup:
                    matching_company = next((name for name in companies.keys() if name.lower() == ai_company_name), None)
                    if matching_company:
                        startup_companies[matching_company] = companies[matching_company].copy()
                        startup_companies[matching_company]['ai_explanation'] = '\n'.join(lines[1:])
                        # Store last email of each thread
                        startup_companies[matching_company]['last_emails'] = [
                            thread[-1] for thread in startup_companies[matching_company]['threads']
                        ]
                        current_app.logger.info(f"Identified startup: {matching_company}")
                    else:
                        current_app.logger.warning(f"Identified startup {ai_company_name} not found in original companies list")

        current_app.logger.info(f"Identified {len(startup_companies)} potential startups")
        return startup_companies
    except Exception as e:
        current_app.logger.error(f"Error in GPT analysis: {str(e)}")
        return {}
    
# Extracts the body content from an email message
async def get_email_body(msg):
    if 'payload' not in msg:
        return msg.get('snippet', '')

    async def decode_body(body):
        if 'data' in body:
            return base64.urlsafe_b64decode(body['data']).decode('utf-8', errors='ignore')
        return ''

    payload = msg['payload']

    if 'body' in payload and payload['body'].get('data'):
        return await decode_body(payload['body'])

    if 'parts' in payload:
        text_content = ''
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                text_content += await decode_body(part['body'])
            elif part['mimeType'] == 'multipart/alternative':
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain':
                        text_content += await decode_body(subpart['body'])
        if text_content:
            return text_content

    return msg.get('snippet', '')

# Extracts an email address from a sender string
def extract_email_address(sender):
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1) if match else sender

# Generates a CSV file containing information about startup companies
def generate_csv(startup_companies):
    filename = 'email_data.csv'
    current_app.logger.info(f"Generating CSV for {len(startup_companies)} startups")
    
    def generate_rows():
        yield ['First Interaction Date', 'Last Interaction Date', 'Company', 'Interactions', 'Last Interaction', 'AI Explanation']
        for company, data in startup_companies.items():
            try:
                all_dates = [email['date'] for thread in data['threads'] for email in thread]
                first_date = min(all_dates)
                last_date = max(all_dates)
                
                first_date_formatted = datetime.strptime(first_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                last_date_formatted = datetime.strptime(last_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                
                total_interactions = sum(len(thread) for thread in data['threads'])
                
                # Get the last email from the most recent thread
                last_email = data['last_emails'][-1] if data['last_emails'] else None
                if last_email:
                    last_interaction = f"{last_email['email']} last sent: {last_email['body'][:100]}..."
                else:
                    last_interaction = "No interaction data available"
                
                yield [
                    first_date_formatted,
                    last_date_formatted,
                    company,
                    total_interactions,
                    last_interaction,
                    data.get('ai_explanation', '')
                ]
            except Exception as e:
                current_app.logger.error(f"Error processing data for {company}: {str(e)}")

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in generate_rows():
            writer.writerow(row)

    current_app.logger.info(f"CSV generated: {filename}")
    return filename

# Summarizes an email thread
def summarize_thread(thread):
    first_email = thread[0]
    last_email = thread[-1]
    
    summary = f"Thread of {len(thread)} emails. "
    summary += f"Started: '{first_email['subject']}'. "
    if len(thread) > 1:
        summary += f"Last: '{last_email['subject']}'. "
    
    content_summary = ". ".join(set(email['body'][:50] + "..." for email in thread))
    summary += f"Content: {content_summary[:100]}..."
    
    return summary

# Processes emails to identify startups
async def process_emails(credentials):
    global progress_tracker
    progress_tracker.update(status="Starting", current_step="Initializing")
    try:
        current_app.logger.info("Starting email processing")
        num_startups, csv_path = await analyze_emails(credentials)
        current_app.logger.info(f"Email processing complete. Found {num_startups} startups.")
        progress_tracker.update(status="Completed", num_startups=num_startups)
        return num_startups, csv_path, None, progress_tracker
    except Exception as e:
        current_app.logger.error(f"Error in email processing: {str(e)}")
        progress_tracker.update(status="Error", current_step=str(e))
        return None, None, str(e), progress_tracker
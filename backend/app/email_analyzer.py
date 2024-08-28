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
from config.settings import MAX_EMAILS, INTERNAL_DOMAINS, BLACKLISTED_DOMAINS
from .models import Company, User
from .extensions import db

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
async def analyze_emails(credentials, user_email, full_reanalysis=False):
    global progress_tracker
    current_app.logger.info("Starting email analysis")
    progress_tracker.update(status="Fetching emails")
    
    service = build('gmail', 'v1', credentials=credentials)
    
    user = User.query.filter_by(email=user_email).first()
    last_analyzed_email_id = None if full_reanalysis else (user.last_analyzed_email_id if user else None)
    
    companies = defaultdict(lambda: {"threads": [], "interactions": 0})
    page_token = None
    processed_emails = 0
    processed_threads = 0
    skipped_threads = 0
    batch_size = 10  # Temporary for testing
    email_batch_size = 5  # Temporary for testing

    current_app.logger.info(f"Fetching a maximum of {MAX_EMAILS} emails")

    try:
        while processed_emails < MAX_EMAILS:
            results = service.users().threads().list(userId='me', maxResults=batch_size, pageToken=page_token).execute()
            threads = results.get('threads', [])
            
            if not threads:
                current_app.logger.info("No more threads to process")
                break

            current_app.logger.info(f"Fetched {len(threads)} threads")
            
            for thread in threads:
                if processed_emails >= MAX_EMAILS:
                    break

                try:
                    thread_data = service.users().threads().get(userId='me', id=thread['id']).execute()
                    thread_messages = thread_data.get('messages', [])
                    
                    # Check if we've reached the last analyzed email
                    if last_analyzed_email_id and thread_messages[0]['id'] == last_analyzed_email_id:
                        current_app.logger.info("Reached last analyzed email, stopping analysis")
                        break
                    
                    # Process emails in smaller batches
                    for i in range(0, len(thread_messages), email_batch_size):
                        email_batch = thread_messages[i:i+email_batch_size]
                        thread_emails = await asyncio.gather(*[extract_email_data(msg) for msg in email_batch])
                        
                        current_app.logger.info(f"Processing batch of {len(thread_emails)} emails from thread {thread['id']}")
                        
                        if not thread_emails:
                            current_app.logger.warning(f"Skipping empty batch in thread: {thread['id']}")
                            continue
                        
                        # Check if the email is between two internal addresses or from a blacklisted domain
                        sender_domain = thread_emails[0]['sender_email'].split('@')[1]
                        recipient_domain = thread_emails[0]['recipient_email'].split('@')[1]
                        if (sender_domain in INTERNAL_DOMAINS and recipient_domain in INTERNAL_DOMAINS) or \
                        (sender_domain in BLACKLISTED_DOMAINS or recipient_domain in BLACKLISTED_DOMAINS):
                            current_app.logger.info(f"Skipped email: {thread_emails[0]['sender_email']} to {thread_emails[0]['recipient_email']}")
                            skipped_threads += 1
                            continue
                        
                        company_name = extract_company_name(thread_emails[0])
                        if company_name:
                            if company_name in companies:
                                current_app.logger.info(f"Adding new emails to existing company: {company_name}")
                                companies[company_name]["threads"].append(thread_emails)
                                companies[company_name]["interactions"] += len(thread_emails)
                            else:
                                current_app.logger.info(f"Adding new company: {company_name}")
                                companies[company_name] = {
                                    "threads": [thread_emails],
                                    "interactions": len(thread_emails),
                                }
                            
                            current_app.logger.info(f"Added {len(thread_emails)} emails to company: {company_name}")
                        
                        processed_emails += len(thread_emails)
                        progress_tracker.update(
                            total_emails=MAX_EMAILS,
                            processed_emails=min(processed_emails, MAX_EMAILS),
                            total_threads=processed_threads + skipped_threads,
                            status=f"Processed {processed_threads} threads, skipped {skipped_threads}, {min(processed_emails, MAX_EMAILS)}/{MAX_EMAILS} emails"
                        )

                        if processed_emails >= MAX_EMAILS:
                            break

                    processed_threads += 1

                except Exception as e:
                    current_app.logger.error(f"Error processing thread {thread['id']}: {str(e)}")
                    skipped_threads += 1

                    # If we encounter an error with the last analyzed email, reset and continue
                    if last_analyzed_email_id and thread['id'] == last_analyzed_email_id:
                        current_app.logger.warning("Last analyzed email not accessible, continuing with full analysis")
                        last_analyzed_email_id = None

            if 'nextPageToken' not in results:
                current_app.logger.info("No more pages to fetch")
                break
            page_token = results['nextPageToken']

        # Update the user's last analyzed email ID and analysis date
        if processed_emails > 0:
            last_email_id = thread_messages[0]['id']
            if user:
                user.last_analyzed_email_id = last_email_id
                user.last_analysis_date = datetime.utcnow()
            else:
                user = User(email=user_email, last_analyzed_email_id=last_email_id, last_analysis_date=datetime.utcnow())
                db.session.add(user)
            db.session.commit()

        current_app.logger.info(f"Processed {processed_threads} threads, skipped {skipped_threads}, {processed_emails} emails. Found {len(companies)} companies")
        progress_tracker.update(total_companies=len(companies), status="Analyzing companies", analyzed_companies=0)
        startup_companies = await analyze_companies(companies)
        progress_tracker.update(status="Generating CSV", num_startups=len(startup_companies))
        csv_path = generate_csv(startup_companies, user_email)
        progress_tracker.update(status="Completed")
        return len(startup_companies), csv_path
    except Exception as e:
        current_app.logger.error(f"Error in analyze_emails: {str(e)}")
        progress_tracker.update(status="Error", current_step=str(e))
        return None, None

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

    recipient = next((header['value'] for header in headers if header['name'].lower() == 'to'), '')
    recipient_email = extract_email_address(recipient)

    email_data = {
        'date': parsed_date,
        'subject': subject,
        'sender': sender,
        'sender_email': extract_email_address(sender),
        'recipient_email': recipient_email,
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
    try:
        sender_domain = email_data['sender_email'].split('@')[1]
        recipient_domain = email_data['recipient_email'].split('@')[1]
        
        if sender_domain in INTERNAL_DOMAINS:
            return recipient_domain if recipient_domain not in INTERNAL_DOMAINS else None
        elif recipient_domain in INTERNAL_DOMAINS:
            return sender_domain
        else:
            return sender_domain if sender_domain not in BLACKLISTED_DOMAINS else None
    except Exception as e:
        current_app.logger.error(f"Error extracting company name: {str(e)}")
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
            print("lines:", lines)
            if len(lines) >= 2:
                ai_company_name = ' '.join(lines[0].replace('Company:', '').strip().strip('*').split()).lower()
                ai_company_name = re.sub(r'^\d+\.\s*', '', ai_company_name)  # Remove leading numbers and dots
                ai_company_name = ai_company_name.strip('*')  # Remove any remaining asterisks
                is_startup = 'yes' in lines[1].strip().lower()
                print("company:", ai_company_name)
                print("is_startup:", is_startup)
                current_app.logger.info(f"AI analysis for {ai_company_name}: {'Startup' if is_startup else 'Not a startup'}")
                if is_startup:
                    matching_company = next((name for name in companies.keys() if ai_company_name in name.lower()), None)
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
def generate_csv(startup_companies, user_email):
    filename = 'email_data.csv'
    current_app.logger.info(f"Generating CSV for {len(startup_companies)} startups")
    
    def generate_rows():
        yield ['First Interaction Date', 'Last Interaction Date', 'Company', 'Interactions', 'Last Interaction', 'AI Explanation']
        for company, data in startup_companies.items():
            try:
                current_app.logger.info(f"Processing data for {company}")
                current_app.logger.debug(f"Data structure: {data}")  # Log the entire data structure

                all_dates = [email['date'] for thread in data['threads'] for email in thread]
                first_date = min(all_dates)
                last_date = max(all_dates)
                
                first_date_formatted = datetime.strptime(first_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                last_date_formatted = datetime.strptime(last_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                
                total_interactions = sum(len(thread) for thread in data['threads'])
                
                # Get the last email from the most recent thread
                last_email = data['last_emails'][-1] if data['last_emails'] else None
                if last_email:
                    last_interaction = f"{last_email.get('sender_email', 'Unknown')} last sent: {last_email['body'][:100]}..."
                else:
                    last_interaction = "No interaction data available"
                
                company_contact = user_email
                
                db_company = Company.query.filter_by(name=company).first()
                if db_company:
                    db_company.last_interaction_date = datetime.strptime(last_date, "%Y-%m-%d").date()
                    db_company.total_interactions = total_interactions
                    db_company.company_contact = company_contact
                    current_app.logger.info(f"Updated company in database: {company}")
                else:
                    db_company = Company(
                        name=company,
                        first_interaction_date=datetime.strptime(first_date, "%Y-%m-%d").date(),
                        last_interaction_date=datetime.strptime(last_date, "%Y-%m-%d").date(),
                        total_interactions=total_interactions,
                        company_contact=company_contact
                    )
                    db.session.add(db_company)
                    current_app.logger.info(f"Added new company to database: {company}")
                db.session.commit()
                
                yield [
                    first_date_formatted,
                    last_date_formatted,
                    company,
                    total_interactions,
                    last_interaction,
                    data.get('ai_explanation', ''),
                    company_contact
                ]
            except Exception as e:
                current_app.logger.error(f"Error processing data for {company}: {str(e)}")
                current_app.logger.error(f"Data causing error: {data}")  # Log the problematic data

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
async def process_emails(credentials, user_email, full_reanalysis=False):
    global progress_tracker
    progress_tracker.update(status="Starting", current_step="Initializing")
    try:
        current_app.logger.info("Starting email processing")
        num_startups, csv_path = await analyze_emails(credentials, user_email, full_reanalysis)
        current_app.logger.info(f"Email processing complete. Found {num_startups} startups.")
        progress_tracker.update(status="Completed", num_startups=num_startups)
        return num_startups, csv_path, None, progress_tracker
    except Exception as e:
        current_app.logger.error(f"Error in email processing: {str(e)}")
        progress_tracker.update(status="Error", current_step=str(e))
        return None, None, str(e), progress_tracker
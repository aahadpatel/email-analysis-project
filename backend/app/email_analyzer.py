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


client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressTracker:
    def __init__(self):
        self.total_emails = 0
        self.processed_emails = 0
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
    
    # Fetch threads instead of individual messages
    # Optimization: Consider limiting the number of threads fetched or implementing pagination
    results = service.users().threads().list(userId='me', maxResults=10).execute()
    threads = results.get('threads', [])
    
    current_app.logger.info(f"Fetched {len(threads)} email threads")
    progress_tracker.update(total_emails=len(threads), status="Processing email threads", processed_emails=0)
    
    companies = defaultdict(lambda: {"threads": [], "interactions": 0})

    for i, thread in enumerate(threads, 1):
        current_app.logger.info(f"Processing thread {i}/{len(threads)}")
        thread_data = service.users().threads().get(userId='me', id=thread['id']).execute()
        thread_emails = [extract_email_data(msg) for msg in thread_data['messages']]
        
        company_name = extract_company_name(thread_emails[0])  # Use the first email to determine the company
        
        if company_name:
            companies[company_name]["threads"].append(thread_emails)
            companies[company_name]["interactions"] += 1
        
        progress_tracker.update(processed_emails=i, status=f"Processing thread {i}/{len(threads)}")

    current_app.logger.info(f"Processed all threads. Found {len(companies)} companies")
    current_app.logger.info(f"Companies before analysis: {', '.join(companies.keys())}")
    progress_tracker.update(total_companies=len(companies), status="Analyzing companies", analyzed_companies=0)
    
    startup_companies = await analyze_companies(companies)
    
    current_app.logger.info(f"Analysis complete. Found {len(startup_companies)} startup companies")
    current_app.logger.info(f"Startup companies: {', '.join(startup_companies.keys())}")
    progress_tracker.update(status="Generating CSV", num_startups=len(startup_companies))
    csv_path = generate_csv(startup_companies)
    
    progress_tracker.update(status="Completed")
    return len(startup_companies), csv_path

# Extracts relevant data from an email message
def extract_email_data(msg):
    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '')
    date = next((header['value'] for header in headers if header['name'].lower() == 'date'), '')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')

    # Optimization: Consider truncating very long email bodies to save on API costs
    body = get_email_body(msg)

    # Log the extracted email data
    current_app.logger.info(f"Extracted email data:")
    current_app.logger.info(f"Subject: {subject}")
    current_app.logger.info(f"Sender: {sender}")
    current_app.logger.info(f"Body (first 200 chars): {body[:200]}")
    current_app.logger.info(f"Body length: {len(body)}")

    parsed_date = parse_date(date)

    return {
        'date': parsed_date,
        'subject': subject,
        'sender': sender,
        'email': extract_email_address(sender),
        'body': body
    }

# Parses a date string into a standard format
def parse_date(date_string):
    """
    Parse the date string into a standard format.
    """
    try:
        dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # If the above format doesn't work, try a more general approach
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
        summary = f"Company: {company_name}\n"
        summary += f"Interactions: {data['interactions']}\n"
        summary += "Email Threads:\n"
        for thread in data['threads']:
            summary += "Thread:\n"
            for email in thread:
                summary += f"Subject: {email.get('subject', 'No subject')}\n"
                body = email.get('body', '')
                if body:
                    summary += f"Body: {body[:500]}...\n"
                else:
                    summary += "Body: No body content\n"
                summary += "\n"
        company_summaries.append(summary)
        progress_tracker.update(analyzed_companies=i, status=f"Analyzing company {i}/{len(companies)}")
        
        current_app.logger.info(f"Summary for {company_name}:\n{summary}")

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

    current_app.logger.info(f"Full prompt for OpenAI:\n{prompt}")

    try:
        # Optimization: Consider batching API calls or limiting the number of companies analyzed at once
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
        
        current_app.logger.info(f"OpenAI Response: {ai_response}")

        startup_companies = {}
        for company_analysis in ai_response.split('\n\n'):
            lines = company_analysis.split('\n')
            print("lines: ", lines)
            if len(lines) >= 2:
                ai_company_name = ' '.join(lines[0].replace('Company:', '').strip().strip('*').split()).lower()
                is_startup = 'yes' in lines[1].strip().lower() 
                current_app.logger.info(f"Analyzing company: {ai_company_name}")
                current_app.logger.info(f"Is startup: {is_startup}")
                current_app.logger.info(f"Analysis: {lines[1]}")
                if is_startup:
                    # Find the matching company in the original list
                    matching_company = next((name for name in companies.keys() if ' '.join(name.split()).lower() == ai_company_name), None)
                    if matching_company:
                        startup_companies[matching_company] = companies[matching_company].copy()
                        startup_companies[matching_company]['ai_explanation'] = '\n'.join(lines[1:])
                        current_app.logger.info(f"Identified startup: {matching_company}")
                        current_app.logger.info(f"  Threads: {len(startup_companies[matching_company]['threads'])}")
                        current_app.logger.info(f"  AI Explanation: {startup_companies[matching_company]['ai_explanation']}")
                    else:
                        current_app.logger.warning(f"Identified startup {ai_company_name} not found in original companies list")
                else:
                    current_app.logger.info(f"{ai_company_name} is not identified as a startup")

        current_app.logger.info(f"Identified {len(startup_companies)} potential startups")
        current_app.logger.info(f"Startup companies: {', '.join(startup_companies.keys())}")
        return startup_companies
    except Exception as e:
        current_app.logger.error(f"Error in GPT analysis: {str(e)}")
        return {}

# Extracts the body content from an email message
def get_email_body(msg):
    logging.info(f"Processing message with ID: {msg.get('id', 'Unknown')}")

    if 'payload' not in msg:
        logging.warning(f"Message {msg.get('id', 'Unknown')} has no 'payload' key")
        return msg.get('snippet', '')

    def decode_body(body):
        if 'data' in body:
            return base64.urlsafe_b64decode(body['data']).decode('utf-8', errors='ignore')
        return ''

    payload = msg['payload']

    if 'body' in payload and payload['body'].get('data'):
        return decode_body(payload['body'])

    if 'parts' in payload:
        text_content = ''
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                text_content += decode_body(part['body'])
            elif part['mimeType'] == 'multipart/alternative':
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain':
                        text_content += decode_body(subpart['body'])
        if text_content:
            return text_content

    logging.warning(f"Unexpected message structure for message {msg.get('id', 'Unknown')}")
    return msg.get('snippet', '')

# Parses a date string into a standard format
def parse_date(date_string):
    """
    Parse the date string into a standard format.
    """
    try:
        # Try parsing with the original format
        dt = datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        try:
            # If that fails, try parsing with the new format
            dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            # If that also fails, use a more flexible parser
            dt = dateutil.parser.parse(date_string)
    
    return dt.strftime("%Y-%m-%d")

# Extracts an email address from a sender string
def extract_email_address(sender):
    """
    Extract email address from sender string.
    """
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1) if match else sender

import csv
from datetime import datetime
from operator import itemgetter

# Generates a CSV file containing information about startup companies
def generate_csv(startup_companies):
    filename = 'email_data.csv'
    csv_data = []

    current_app.logger.info(f"Generating CSV for {len(startup_companies)} startups")

    for company, data in startup_companies.items():
        current_app.logger.info(f"Processing data for {company}:")
        
        try:
            # Count total emails in all threads
            total_interactions = sum(len(thread) for thread in data['threads'])
            current_app.logger.info(f"  Interactions: {total_interactions}")
            current_app.logger.info(f"  Number of threads: {len(data['threads'])}")
            
            # Get first and last interaction dates
            all_dates = [email['date'] for thread in data['threads'] for email in thread]
            first_date = min(all_dates)
            last_date = max(all_dates)
            
            # Format dates
            first_date_formatted = datetime.strptime(first_date, "%Y-%m-%d").strftime("%m-%d-%Y")
            last_date_formatted = datetime.strptime(last_date, "%Y-%m-%d").strftime("%m-%d-%Y")
            
            # Summarize all threads
            all_threads_summary = []
            for thread in data['threads']:
                thread_summary = summarize_thread(thread)
                all_threads_summary.append(thread_summary)
            
            # Join all thread summaries, limiting to 100 words
            summary = ' '.join(all_threads_summary)
            summary = ' '.join(summary.split()[:100])  # Limit to 100 words
            
            current_app.logger.info(f"  Thread summary: {summary[:200]}...")
            
            csv_data.append([
                first_date_formatted,
                last_date_formatted,
                company,
                total_interactions,
                summary,
                data.get('ai_explanation', '')
            ])
        except Exception as e:
            current_app.logger.error(f"Error processing data for {company}: {str(e)}")

    current_app.logger.info(f"CSV data prepared with {len(csv_data)} rows")

    # Sort by last interaction date, most recent first
    csv_data.sort(key=lambda x: datetime.strptime(x[1], "%m-%d-%Y"), reverse=True)

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['First Interaction Date', 'Last Interaction Date', 'Company', 'Interactions', 'Email Thread Summary', 'AI Explanation'])
        writer.writerows(csv_data)

    current_app.logger.info(f"CSV generated: {filename} with {len(csv_data)} startups")
    current_app.logger.info(f"Startup companies: {', '.join(startup_companies.keys())}")
    return filename

# Summarizes an email thread
def summarize_thread(thread):
    # Extract key information from the thread
    first_email = thread[0]
    last_email = thread[-1]
    
    # Create a summary
    summary = f"Thread of {len(thread)} emails. "
    summary += f"Started: '{first_email['subject']}'. "
    if len(thread) > 1:
        summary += f"Last: '{last_email['subject']}'. "
    
    # Add a brief content summary (you might want to use AI for a more sophisticated summary)
    content_summary = ". ".join(set(email['body'][:50] + "..." for email in thread))
    summary += f"Content: {content_summary[:100]}..."
    
    return summary

# Processes emails to identify startups
async def process_emails(credentials):
    global progress_tracker
    current_app.logger.info("process_emails function called")
    progress_tracker.update(status="Starting", current_step="Initializing")
    try:
        current_app.logger.info("Starting email analysis process")
        current_app.logger.info("About to call analyze_emails")
        num_startups, csv_path = await analyze_emails(credentials)
        current_app.logger.info(f"Email analysis complete. Found {num_startups} startups.")
        progress_tracker.update(status="Completed", num_startups=num_startups)
        return num_startups, csv_path, None, progress_tracker
    except Exception as e:
        current_app.logger.error(f"Error in email analysis: {str(e)}")
        progress_tracker.update(status="Error", current_step=str(e))
        return None, None, str(e), progress_tracker
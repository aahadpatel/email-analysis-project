import asyncio
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import csv
from datetime import datetime
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
        self.startup_companies = {}
        self.lock = threading.Lock()

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)
            current_app.logger.info(f"Progress update: {self.status} - Emails: {self.processed_emails}/{self.total_emails}, Companies: {self.analyzed_companies}/{self.total_companies}, Startups: {len(self.startup_companies)}")

progress = ProgressTracker()


async def analyze_emails(credentials):
    global progress
    current_app.logger.info("Starting email analysis")
    progress.update(status="Fetching emails")
    
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    
    current_app.logger.info(f"Fetched {len(messages)} emails")
    progress.update(total_emails=len(messages), status="Processing emails")
    
    companies = defaultdict(lambda: {"emails": [], "interactions": 0})

    for i, message in enumerate(messages, 1):
        current_app.logger.info(f"Processing email {i}/{len(messages)}")
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        email_data = extract_email_data(msg)
        company_name = extract_company_name(email_data)
        
        if company_name:
            companies[company_name]["emails"].append(email_data)
            companies[company_name]["interactions"] += 1
        
        progress.update(processed_emails=i)

    current_app.logger.info(f"Processed all emails. Found {len(companies)} companies")
    progress.update(total_companies=len(companies), status="Analyzing companies")
    
    startup_companies = await analyze_companies(companies)
    
    current_app.logger.info(f"Analysis complete. Found {len(startup_companies)} startup companies")
    current_app.logger.info(f"Startup companies: {', '.join(startup_companies.keys())}")
    progress.update(status="Generating CSV", startup_companies=startup_companies)
    csv_path = generate_csv(startup_companies)
    
    progress.update(status="Completed")
    return len(startup_companies), csv_path

def extract_email_data(msg):
    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '')
    date = next((header['value'] for header in headers if header['name'].lower() == 'date'), '')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')

    body = get_email_body(msg)

    # Log the extracted email data
    current_app.logger.info(f"Extracted email data:")
    current_app.logger.info(f"Subject: {subject}")
    current_app.logger.info(f"Sender: {sender}")
    current_app.logger.info(f"Body (first 200 chars): {body[:200]}")
    current_app.logger.info(f"Body length: {len(body)}")

    return {
        'date': parse_date(date),
        'subject': subject,
        'sender': sender,
        'email': extract_email_address(sender),
        'body': body
    }

def extract_company_name(email_data):
    domain = email_data['email'].split('@')[1]
    if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
        return domain
    return None

async def analyze_companies(companies):
    global progress
    company_summaries = []
    for i, (company_name, data) in enumerate(companies.items(), 1):
        summary = f"Company: {company_name}\n"
        summary += f"Interactions: {data['interactions']}\n"
        summary += "Email Content:\n"
        for email in data['emails']:
            summary += f"Subject: {email.get('subject', 'No subject')}\n"
            body = email.get('body', '')
            if body:
                summary += f"Body: {body[:1000]}...\n"
            else:
                summary += "Body: No body content\n"
            summary += "\n"
        company_summaries.append(summary)
        progress.update(analyzed_companies=i)
        
        # Log the summary for each company
        current_app.logger.info(f"Summary for {company_name}:\n{summary}")

    prompt = f"""
    Analyze the following email content for each company and determine if they are startups that our venture capital firm might be considering for investment. Focus primarily on the email body content, not just the subject lines. Look for the following indicators:

    1. Discussions about funding rounds, investments, or pitching to investors
    2. If a company is sending over a deck and/or financials, it's likely a startup, but understand context to make sure it's not just a service we're considering paying for.
    3. Requests for meetings, demos, or further discussions with investors
    4. Mentions of product launches, growth metrics, or market opportunities
    5. Any indication of early-stage or innovative technology

    For each company, provide a concise analysis:
    1. Clearly state if this is likely a startup (Yes/No/Insufficient Information)
    2. Briefly explain your reasoning (1-2 sentences)
    3. If it's a startup or potentially a startup, summarize what stage they seem to be at and what they're looking for

    If there's insufficient information, still consider the company name and any context clues. For example, if the company name sounds like a product or service, it might be a startup even with limited email content.

    if it's from fireflies.ai, it's not a startup. if it's from a mucker.com or muckercapital.com email address, it's not a startup.
    Be thorough in your analysis and err on the side of identifying potential startups, even if the evidence is not conclusive.

    {' '.join(company_summaries)}
    """

    # Log the full prompt
    current_app.logger.info(f"Full prompt for OpenAI:\n{prompt}")

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
        
        current_app.logger.info(f"OpenAI Response: {ai_response}")

        startup_companies = {}
        for company_analysis in ai_response.split('\n\n'):
            lines = company_analysis.split('\n')
            if len(lines) >= 2:
                company_name = lines[0].replace('Company:', '').strip()
                is_startup = 'Likely a startup: Yes' in lines[1]
                if is_startup:
                    startup_companies[company_name] = companies[company_name].copy()
                    startup_companies[company_name]['ai_explanation'] = '\n'.join(lines[1:])
                    current_app.logger.info(f"Identified startup: {company_name}")
                    current_app.logger.info(f"  Interactions: {startup_companies[company_name]['interactions']}")
                    current_app.logger.info(f"  Emails: {len(startup_companies[company_name]['emails'])}")
                    current_app.logger.info(f"  AI Explanation: {startup_companies[company_name]['ai_explanation']}")

        current_app.logger.info(f"Identified {len(startup_companies)} potential startups")
        return startup_companies
    except Exception as e:
        current_app.logger.error(f"Error in GPT analysis: {e}")
        return {}

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

def parse_date(date_string):
    """
    Parse the date string into a standard format.
    """
    try:
        dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_string  # Return original string if parsing fails

def extract_email_address(sender):
    """
    Extract email address from sender string.
    """
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1) if match else sender

def generate_csv(startup_companies):
    filename = 'email_data.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Company', 'Interactions', 'Email Subjects', 'Email Bodies', 'AI Explanation'])
        for company, data in startup_companies.items():
            current_app.logger.info(f"Writing data for {company}:")
            current_app.logger.info(f"  Interactions: {data.get('interactions', 0)}")
            current_app.logger.info(f"  Number of emails: {len(data.get('emails', []))}")
            subjects = '; '.join(email.get('subject', '') for email in data.get('emails', []))
            bodies = '; '.join((email.get('body', '')[:200] + '...') for email in data.get('emails', []))
            current_app.logger.info(f"  Subjects: {subjects}")
            current_app.logger.info(f"  Bodies: {bodies[:200]}...")
            writer.writerow([
                company,
                data.get('interactions', 0),
                subjects,
                bodies,
                data.get('ai_explanation', '')
            ])
    current_app.logger.info(f"CSV generated: {filename} with {len(startup_companies)} startups")
    current_app.logger.info(f"Startup companies: {', '.join(startup_companies.keys())}")
    return filename

# This function can be called from your Flask route
async def process_emails(credentials):
    global progress
    progress = ProgressTracker()  # Reset progress for each new analysis
    try:
        num_startups, csv_path = await analyze_emails(credentials)
        return num_startups, csv_path, None, progress
    except Exception as e:
        progress.update(status="Error")
        return None, None, str(e), progress
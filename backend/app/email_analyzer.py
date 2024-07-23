from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import csv
from datetime import datetime
import base64
import re
import logging
from openai import OpenAI
import os
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential


client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def analyze_emails(credentials):
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    startup_data = []
    batch = service.new_batch_http_request()

    def callback(request_id, response, exception):
        if exception is not None:
            print(f"Error processing message {request_id}: {exception}")
            return
        email_data = extract_email_data(response)
        if is_startup_email(email_data):
            startup_data.append(email_data)

    for message in messages:
        batch.add(service.users().messages().get(userId='me', id=message['id']), callback=callback)

    batch.execute()
    generate_csv(startup_data)
    return len(startup_data)

def extract_email_data(msg):
    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '')
    date = next((header['value'] for header in headers if header['name'].lower() == 'date'), '')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')

    body = get_email_body(msg)

    return {
        'date': parse_date(date),
        'subject': subject,
        'sender': sender,
        'email': extract_email_address(sender),
        'body': body
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def is_startup_email(email_data):
    prompt = f"""
    Analyze the following email and determine if it's from or about a startup company that our venture capital firm might be considering for investment. 
    Consider the following criteria:
    1. Is this an inbound email from a startup seeking funding?
    2. Is this a conversation between our team member and a startup about setting up a meeting?
    3. Is there any mention of a pitch deck, financial model, or other startup-related documents?
    4. Does the content suggest this is a potential investment opportunity for our VC firm?
    5. Are there any keywords like "startup", "funding", "investment", "pitch", or "venture"?
    6. Is there discussion about company growth, market opportunity, or innovative technology?

    Email Subject: {email_data['subject']}
    Email Body: {email_data['body'][:1000]}

    Respond with 'Yes' if this email is likely related to a potential startup investment, and 'No' if it's not. 
    If 'Yes', briefly explain why. Be sure to err on the side of inclusion if there's any doubt.
    """

    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an AI assistant analyzing emails for a venture capital firm."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        n=1,
        temperature=0.5)

        ai_response = response.choices[0].message.content.strip()
        is_startup = ai_response.lower().startswith('yes')

        if is_startup:
            email_data['ai_explanation'] = ai_response

        # Add a small delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))

        return is_startup
    except client.RateLimitError as e:
        print(f"Rate limit error: {e}")
        raise
    except client.APIError as e:
        print(f"API error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

def get_email_body(msg):
    logging.info(f"Processing message with ID: {msg.get('id', 'Unknown')}")

    if 'payload' not in msg:
        logging.warning(f"Message {msg.get('id', 'Unknown')} has no 'payload' key")
        return msg.get('snippet', '')

    payload = msg['payload']

    if 'body' in payload:
        body = payload['body']
    elif 'parts' in payload:
        body = payload['parts'][0]['body']
    else:
        logging.warning(f"Unexpected message structure for message {msg.get('id', 'Unknown')}")
        return msg.get('snippet', '')

    if 'data' in body:
        return base64.urlsafe_b64decode(body['data']).decode()
    else:
        return body.get('snippet', '')

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

def generate_csv(data):
    filename = 'email_data.csv'
    fieldnames = ['date', 'subject', 'sender', 'email', 'body_snippet', 'body', 'ai_explanation']
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({k: v for k, v in row.items() if k in fieldnames})
    return filename

# This function can be called from your Flask route
def process_emails(credentials):
    try:
        num_startups = analyze_emails(credentials)
        csv_path = 'email_data.csv'  # Assuming this is where the CSV is saved
        return num_startups, csv_path, None
    except Exception as e:
        return None, None, str(e)
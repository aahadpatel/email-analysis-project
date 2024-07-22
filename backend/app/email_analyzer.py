from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import csv
from datetime import datetime
import base64
import re
import logging

def analyze_emails(credentials):
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    email_data = []

    for message in messages:
        try:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            email_info = extract_email_data(msg)
            if email_info:
                email_data.append(email_info)
        except Exception as e:
            logging.error(f"Error processing message {message['id']}: {str(e)}", exc_info=True)

    generate_csv(email_data)
    return len(email_data)

def extract_email_data(msg):
    try:
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
            'body_snippet': body[:100]  # First 100 characters of the body
        }
    except Exception as e:
        logging.error(f"Error extracting email data: {str(e)}", exc_info=True)
        return None

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
    """
    Generate a CSV file with the extracted email data.
    """
    filename = 'email_data.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'subject', 'sender', 'email', 'body_snippet'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    return filename

# This function can be called from your Flask route
def process_emails(credentials):
    num_emails = analyze_emails(credentials)
    return num_emails, 'email_data.csv'
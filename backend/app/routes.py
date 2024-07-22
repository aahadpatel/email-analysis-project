import os
from flask import current_app, Blueprint, jsonify, request, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from .email_analyzer import process_emails

if os.getenv('OAUTHLIB_INSECURE_TRANSPORT') == '1':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

bp = Blueprint('main', __name__)

def get_client_secrets_file():
    return os.path.join(current_app.instance_path, 'client_secret.json')

@bp.route('/test', methods=['GET'])
def test():
    current_app.logger.info("Test route accessed")
    return jsonify({"message": "CORS test successful"}), 200

@bp.route('/login')
def login():
    current_app.logger.info("Login route accessed")
    try:
        flow = Flow.from_client_secrets_file(
            get_client_secrets_file(), 
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        flow.redirect_uri = url_for('main.oauth2callback', _external=True)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session['state'] = state
        return jsonify({'authorization_url': authorization_url})
    except Exception as e:
        current_app.logger.error(f"Error in login route: {str(e)}")
        return jsonify({"error": "Failed to generate authorization URL", "details": str(e)}), 500

@bp.route('/oauth2callback')
def oauth2callback():
    current_app.logger.info("OAuth callback route accessed")
    try:
        state = session['state']
        flow = Flow.from_client_secrets_file(
            get_client_secrets_file(),
            scopes=['https://www.googleapis.com/auth/gmail.readonly'],
            state=state
        )
        flow.redirect_uri = url_for('main.oauth2callback', _external=True)

        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)

        current_app.logger.info("Authentication successful")
        return jsonify({"message": "Authentication successful"})
    except Exception as e:
        current_app.logger.error(f"Error in OAuth callback: {str(e)}")
        return jsonify({"error": "Authentication failed", "details": str(e)}), 400

@bp.route('/analyze_emails', methods=['GET'])
def analyze_emails():
    if 'credentials' not in session:
        current_app.logger.error("Attempt to analyze emails without credentials")
        return jsonify({"error": "Not authenticated"}), 401

    try:
        credentials = Credentials(**session['credentials'])
        current_app.logger.info("Credentials retrieved from session")
        
        num_emails = process_emails(credentials)
        current_app.logger.info(f"Email analysis complete. Analyzed {num_emails} emails")
        
        return jsonify({"num_emails": num_emails, "csv_path": "path/to/your/csv/file.csv"})
    except Exception as e:
        current_app.logger.error(f"Error in analyze_emails: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while analyzing emails"}), 500
     
def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

@bp.route('/', defaults={'path': ''})
@bp.route('/<path:path>')
def catch_all(path):
    current_app.logger.warning(f"Accessed undefined route: {path}")
    return jsonify({"error": "Route not found"}), 404

@bp.route('/check_auth', methods=['GET'])
def check_auth():
    is_authenticated = 'credentials' in session
    return jsonify({"is_authenticated": is_authenticated})
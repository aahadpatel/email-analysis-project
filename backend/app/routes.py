import os
import threading
from flask import current_app, Blueprint, jsonify, request, url_for, session, redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token
from .email_analyzer import process_emails
import asyncio
from .email_analyzer import process_emails, progress_tracker
from .models import Company
from .extensions import db
from sqlalchemy import text

ALLOWED_DOMAINS = ['muckercapital.com', 'mucker.com']

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
            scopes=['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/userinfo.email', 'openid']
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
            scopes=['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/userinfo.email', 'openid'],
            state=state
        )
        flow.redirect_uri = url_for('main.oauth2callback', _external=True)

        current_app.logger.info("Fetching token...")
        flow.fetch_token(authorization_response=request.url)
        current_app.logger.info("Token fetched successfully")

        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'id_token': credentials.id_token,  # Store the id_token
        }
        
        request_obj = google_auth_requests.Request()
        
        current_app.logger.info("Verifying ID token...")
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, request_obj, credentials.client_id)
        current_app.logger.info("ID token verified successfully")

        email = id_info.get('email')
        session['user_email'] = email  # Store the email in the session
        domain = email.split('@')[1]
        current_app.logger.info(f"Email: {email}, Domain: {domain}")

        if domain not in ALLOWED_DOMAINS:
            current_app.logger.warning(f"Unauthorized access attempt from domain: {domain}")
            return redirect('http://localhost:3000/unauthorized')

        session.modified = True  # Ensure the session is saved

        current_app.logger.info("Authentication successful")
        return redirect('http://localhost:3000/dashboard')
    except Exception as e:
        current_app.logger.error(f"Error in OAuth callback: {str(e)}")
        return redirect('http://localhost:3000/auth-error')
    

@bp.route('/create_table', methods=['GET'])
def create_table():
    try:
        with current_app.app_context():
            db.create_all()
            return jsonify({"message": "Table created successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Error creating table: {str(e)}")
        return jsonify({"error": f"Failed to create table: {str(e)}"}), 500
    
@bp.route('/analyze_emails', methods=['GET'])
async def analyze_emails():
    if 'credentials' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    credentials = Credentials(**session['credentials'])
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({"error": "User email not found"}), 400

    try:
        num_startups, csv_path, error, _ = await process_emails(credentials, user_email)
        if error:
            return jsonify({"error": "Email analysis failed", "details": error}), 500
        if num_startups is None or csv_path is None:
            return jsonify({"error": "Email analysis returned unexpected results"}), 500
        return jsonify({
            "num_startups": num_startups,
            "csv_path": csv_path,
            "message": f"Analysis complete. Found {num_startups} startup-related emails."
        })
    except Exception as e:
        return jsonify({
            "error": "Analysis failed",
            "message": str(e)
        }), 500
    
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

@bp.route('/db_test', methods=['GET'])
def db_test():
    try:
        with current_app.app_context():
            result = db.session.execute(text('SELECT 1'))
            current_app.logger.info(f"Database test result: {result.fetchone()}")
        return jsonify({"message": "Database connection successful"}), 200
    except Exception as e:
        current_app.logger.error(f"Database connection error: {str(e)}")
        return jsonify({"error": f"Database connection failed: {str(e)}"}), 500

@bp.route('/companies', methods=['GET'])
def get_companies():
    try:
        companies = Company.query.all()
        company_list = [{
            'name': c.name,
            'first_interaction_date': c.first_interaction_date.strftime('%Y-%m-%d'),
            'last_interaction_date': c.last_interaction_date.strftime('%Y-%m-%d'),
            'total_interactions': c.total_interactions,
            'company_contact': c.company_contact
        } for c in companies]
        current_app.logger.info(f"Retrieved {len(company_list)} companies from the database")
        return jsonify(company_list)
    except Exception as e:
        current_app.logger.error(f"Error in get_companies route: {str(e)}")
        return jsonify({"error": "An error occurred while retrieving companies"}), 500

@bp.route('/check_auth', methods=['GET'])
def check_auth():
    is_authenticated = 'credentials' in session
    email = None
    if is_authenticated:
        try:
            credentials = Credentials(
                token=session['credentials']['token'],
                refresh_token=session['credentials']['refresh_token'],
                token_uri=session['credentials']['token_uri'],
                client_id=session['credentials']['client_id'],
                client_secret=session['credentials']['client_secret'],
                scopes=session['credentials']['scopes']
            )
            request_obj = google_auth_requests.Request()
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(request_obj)
                # Update session with refreshed credentials
                session['credentials']['token'] = credentials.token
                session.modified = True

            if 'id_token' in session['credentials']:
                id_info = id_token.verify_oauth2_token(
                    session['credentials']['id_token'], request_obj, credentials.client_id)
                email = id_info.get('email')
            else:
                email = session.get('user_email')  # Fallback to stored email
        except Exception as e:
            current_app.logger.error(f"Error verifying token: {str(e)}")
            is_authenticated = False
    return jsonify({
        "is_authenticated": is_authenticated,
        "email": email
    })

# Global dictionary to store analysis tasks
analysis_tasks = {}

@bp.route('/start_analysis', methods=['POST'])
def start_analysis():
    if 'credentials' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    credentials = Credentials(**session['credentials'])
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({"error": "User email not found"}), 400
    
    def run_analysis_in_thread(app, credentials, user_email):
        with app.app_context():
            global progress_tracker
            current_app.logger.info("Analysis thread started")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                num_startups, csv_path, error, _ = loop.run_until_complete(process_emails(credentials, user_email))
                if error:
                    progress_tracker.update(status="Error", current_step=str(error))
                else:
                    progress_tracker.update(status="Completed", num_startups=num_startups)
                current_app.logger.info(f"Analysis completed. num_startups: {num_startups}, csv_path: {csv_path}, error: {error}")
            except Exception as e:
                current_app.logger.error(f"Error in analysis thread: {str(e)}")
                progress_tracker.update(status="Error", current_step=str(e))
            finally:
                loop.close()
            current_app.logger.info("Analysis thread finished")

    app = current_app._get_current_object()
    threading.Thread(target=run_analysis_in_thread, args=(app, credentials, user_email)).start()
    current_app.logger.info("Analysis thread created and started")
    
    return jsonify({"message": "Analysis started"}), 202

def run_analysis(app, credentials, user_email):
    with app.app_context():
        current_app.logger.info("Starting analysis...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            current_app.logger.info("Created new event loop")
            num_startups, csv_path, error, _ = loop.run_until_complete(process_emails(credentials, user_email))
            current_app.logger.info(f"Analysis completed. num_startups: {num_startups}, csv_path: {csv_path}, error: {error}")
            if error:
                current_app.logger.error(f"Error in email analysis: {error}")
            else:
                current_app.logger.info(f"Analysis complete. Found {num_startups} startup-related emails.")
        except Exception as e:
            current_app.logger.error(f"Unexpected error in email analysis: {str(e)}")
        finally:
            loop.close()
            current_app.logger.info("Event loop closed")


@bp.route('/analysis_progress/<task_id>', methods=['GET'])
def analysis_progress(task_id):
    task = analysis_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@bp.route('/check_progress', methods=['GET'])
def check_progress():
    global progress_tracker
    current_app.logger.info(f"Check progress called. Current progress: {progress_tracker.get_state()}")
    return jsonify(progress_tracker.get_state())

@bp.route('/startups', methods=['GET'])
def get_startups():
    try:
        startups = Company.query.all()
        startup_list = [{
            'name': s.name,
            'first_interaction_date': s.first_interaction_date.strftime('%Y-%m-%d'),
            'last_interaction_date': s.last_interaction_date.strftime('%Y-%m-%d'),
            'total_interactions': s.total_interactions,
            'company_contact': s.company_contact,
            'analysis_date': s.analysis_date.strftime('%Y-%m-%d %H:%M:%S')
        } for s in startups]
        current_app.logger.info(f"Retrieved {len(startup_list)} startups from the database")
        return jsonify(startup_list)
    except Exception as e:
        current_app.logger.error(f"Error in get_startups route: {str(e)}")
        return jsonify({"error": "An error occurred while retrieving startups"}), 500
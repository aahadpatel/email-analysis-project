import os
import threading
from flask import current_app, Blueprint, jsonify, request, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from .email_analyzer import ProgressTracker, process_emails
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import uuid
import asyncio
from .email_analyzer import process_emails, progress_tracker
import threading
import asyncio

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
async def analyze_emails():
    if 'credentials' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    credentials = Credentials(**session['credentials'])

    try:
        num_startups, csv_path, error = await process_emails(credentials)
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

@bp.route('/check_auth', methods=['GET'])
def check_auth():
    is_authenticated = 'credentials' in session
    return jsonify({"is_authenticated": is_authenticated})

# Global dictionary to store analysis tasks
analysis_tasks = {}

@bp.route('/start_analysis', methods=['POST'])
def start_analysis():
    if 'credentials' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    credentials = Credentials(**session['credentials'])
    
    def run_analysis_in_thread(app):
        with app.app_context():
            global progress_tracker
            current_app.logger.info("Analysis thread started")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(process_emails(credentials))
            except Exception as e:
                current_app.logger.error(f"Error in analysis thread: {str(e)}")
                progress_tracker.update(status="Error", current_step=str(e))
            finally:
                loop.close()
            current_app.logger.info("Analysis thread finished")

    app = current_app._get_current_object()
    threading.Thread(target=run_analysis_in_thread, args=(app,)).start()
    current_app.logger.info("Analysis thread created and started")
    
    return jsonify({"message": "Analysis started"}), 202

def run_analysis(app, credentials):
    with app.app_context():
        current_app.logger.info("Starting analysis...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            current_app.logger.info("Created new event loop")
            num_startups, csv_path, error, _ = loop.run_until_complete(process_emails(credentials))
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

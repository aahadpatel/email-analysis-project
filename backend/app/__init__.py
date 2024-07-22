from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)
    
    # Use the secret key from the environment variable
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    
    if not app.secret_key:
        raise ValueError("No FLASK_SECRET_KEY set for Flask application")
    
    app.config.from_mapping(
        SECRET_KEY='dev',  # Change this to a random string in production
    )

    from . import routes
    app.register_blueprint(routes.bp)

    return app
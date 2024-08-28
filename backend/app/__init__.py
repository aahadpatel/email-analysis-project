from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from .extensions import db
from flask_login import LoginManager  # Add this import

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)
    
    # Use the secret key from the environment variable
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    
    if not app.secret_key:
        raise ValueError("No FLASK_SECRET_KEY set for Flask application")

    # Configure the SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the database
    db.init_app(app)

    # Create the database tables
    with app.app_context():
        try:
            from .models import Company  # Import the model here
            db.create_all()
            app.logger.info("Database tables created successfully")

            # Verify if the table was created
            if Company.__table__.exists(db.engine):
                app.logger.info("Company table exists")
            else:
                app.logger.error("Company table does not exist")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}")

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # Import here to avoid circular imports
        return User.query.get(int(user_id))

    # Import and register blueprint
    from . import routes
    app.register_blueprint(routes.bp)

    return app
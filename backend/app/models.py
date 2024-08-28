from flask_sqlalchemy import SQLAlchemy
from .extensions import db
from datetime import datetime
from flask_login import UserMixin
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    first_interaction_date = db.Column(db.Date, nullable=False)
    last_interaction_date = db.Column(db.Date, nullable=False)
    total_interactions = db.Column(db.Integer, default=0)
    company_contact = db.Column(db.String(255))
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Company {self.name}>'
    
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    last_analyzed_email_id = db.Column(db.String(255))
    last_analysis_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<User {self.email}>'
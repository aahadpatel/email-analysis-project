from flask_sqlalchemy import SQLAlchemy
from .extensions import db
from datetime import datetime

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
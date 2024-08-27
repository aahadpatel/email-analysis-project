from flask_sqlalchemy import SQLAlchemy
from .extensions import db

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    first_interaction_date = db.Column(db.Date, nullable=False)
    last_interaction_date = db.Column(db.Date, nullable=False)
    total_interactions = db.Column(db.Integer, default=0)
    company_contact = db.Column(db.String(255))

    def __repr__(self):
        return f'<Company {self.name}>'
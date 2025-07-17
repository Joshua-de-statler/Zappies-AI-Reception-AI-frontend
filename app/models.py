# app/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy here, but tie it to the Flask app later in create_app()
db = SQLAlchemy()

class Company(db.Model):
    __tablename__ = 'companies' # Explicitly set table name for clarity
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    # You might add other company details here like WhatsApp Business Account ID later
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to statistics: one company can have many statistics entries
    # 'bot_statistics' is the backref name that will be added to the BotStatistic model
    bot_statistics = db.relationship('BotStatistic', backref='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.name}>'

class BotStatistic(db.Model):
    __tablename__ = 'bot_statistics' # Explicitly set table name for clarity
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False) # Link to Company table
    
    # Metrics to track
    conversions = db.Column(db.Integer, default=0) # Number of conversions from leads
    
    # For response times, we'll store sum of times and count to calculate average
    total_user_response_time = db.Column(db.Float, default=0.0) # Sum of times it takes for users to respond to bot
    user_response_count = db.Column(db.Integer, default=0)     # Number of user responses measured

    num_recipients = db.Column(db.Integer, default=0)     # Number of unique recipients bot interacted with
    
    # Timestamp for when this statistic entry was recorded/updated
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BotStatistic Company:{self.company_id} At:{self.timestamp}>'

    @property
    def average_user_response_time(self):
        if self.user_response_count > 0:
            return self.total_user_response_time / self.user_response_count
        return 0.0
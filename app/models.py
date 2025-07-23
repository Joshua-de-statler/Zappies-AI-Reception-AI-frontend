from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json # Import json for handling JSON data type for details field
from sqlalchemy.dialects.postgresql import JSONB # Use JSONB for PostgreSQL for better performance with JSON

# Initialize SQLAlchemy. This 'db' object will be imported by other modules.
db = SQLAlchemy()

# --- Company Model ---
class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    whatsapp_users = db.relationship('WhatsAppUser', backref='company', lazy=True)
    conversations = db.relationship('Conversation', backref='company_conv', lazy=True)
    bot_statistics = db.relationship('BotStatistic', backref='company_stats', lazy=True, uselist=False) # One-to-one

    def __repr__(self):
        return f"<Company {self.name}>"

# --- WhatsAppUser Model ---
class WhatsAppUser(db.Model):
    __tablename__ = 'whatsapp_users'
    id = db.Column(db.Integer, primary_key=True)
    wa_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # WhatsApp ID (phone number)
    name = db.Column(db.String(120), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    conversations = db.relationship('Conversation', backref='whatsapp_user', lazy=True)

    def __repr__(self):
        return f"<WhatsAppUser {self.name} ({self.wa_id})>"

# --- Conversation Model ---
class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('whatsapp_users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False) # e.g., 'active', 'closed', 'pending_human'

    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True)
    conversion_events = db.relationship('ConversionEvent', backref='conversation', lazy=True)

    def __repr__(self):
        return f"<Conversation {self.id} for User {self.user_id}>"

# --- Message Model ---
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    response_to_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True) # For bot responses

    # Relationship for linking responses
    response_to = db.relationship('Message', remote_side=[id], backref='responses', lazy=True)

    def __repr__(self):
        return f"<Message {self.id} ({self.sender_type}): {self.content[:30]}...>"

# --- ConversionEvent Model ---
class ConversionEvent(db.Model):
    __tablename__ = 'conversion_events'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # e.g., 'lead_qualified', 'consultation_booked', 'product_interest'
    # Use JSONB for PostgreSQL for efficient storage and querying of JSON data
    details = db.Column(JSONB, nullable=True) # Stores additional event details as JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ConversionEvent {self.id} ({self.event_type}) for Conversation {self.conversation_id}>"

# --- BotStatistic Model ---
class BotStatistic(db.Model):
    __tablename__ = 'bot_statistics'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), unique=True, nullable=False) # One-to-one with Company
    total_messages = db.Column(db.Integer, default=0, nullable=False)
    total_recipients = db.Column(db.Integer, default=0, nullable=False) # Unique users
    total_conversions = db.Column(db.Integer, default=0, nullable=False)
    avg_response_time_ms = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<BotStatistic for Company {self.company_id}>"
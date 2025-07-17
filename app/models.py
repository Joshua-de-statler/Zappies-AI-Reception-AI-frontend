# app/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid # Import uuid for generating UUIDs

# Initialize SQLAlchemy here, but tie it to the Flask app later in create_app()
db = SQLAlchemy()

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Use UUID
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (not direct columns, but for SQLAlchemy to understand links)
    bot_statistics = db.relationship('BotStatistic', backref='company', lazy=True)
    whatsapp_users = db.relationship('WhatsappUser', backref='company', lazy=True)
    conversations = db.relationship('Conversation', backref='company', lazy=True)
    conversion_events = db.relationship('ConversionEvent', backref='company', lazy=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Company {self.name}>'

class WhatsappUser(db.Model):
    __tablename__ = 'whatsapp_users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Internal User ID (UUID)
    wa_id = db.Column(db.String(50), unique=True, nullable=False) # WhatsApp ID (phone number ID from webhook)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    first_interaction_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_interaction_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = db.relationship('Conversation', backref='whatsapp_user', lazy=True)
    conversion_events = db.relationship('ConversionEvent', backref='whatsapp_user', lazy=True)

    def __init__(self, wa_id, company_id, name=None):
        self.wa_id = wa_id
        self.company_id = company_id
        self.name = name

    def __repr__(self):
        return f'<WhatsappUser {self.wa_id}>'

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Conversation ID (UUID)
    user_id = db.Column(db.String(36), db.ForeignKey('whatsapp_users.id'), nullable=False)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='active') # e.g., 'active', 'closed', 'converted_lead', 'abandoned'

    messages = db.relationship('Message', backref='conversation', lazy=True)
    conversion_events = db.relationship('ConversionEvent', backref='conversation', lazy=True)

    def __init__(self, user_id, company_id):
        self.user_id = user_id
        self.company_id = company_id

    def __repr__(self):
        return f'<Conversation {self.id} User:{self.user_id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Message ID (UUID)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    # This links a user's message to the bot's preceding message it's replying to for response time calculation
    response_to_message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=True)

    def __init__(self, conversation_id, sender_type, content, response_to_message_id=None):
        self.conversation_id = conversation_id
        self.sender_type = sender_type
        self.content = content
        self.response_to_message_id = response_to_message_id

    def __repr__(self):
        return f'<Message {self.id} From:{self.sender_type}>'

class ConversionEvent(db.Model):
    __tablename__ = 'conversion_events'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Event ID (UUID)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('whatsapp_users.id'), nullable=False)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)
    event_type = db.Column(db.String(100), nullable=False) # e.g., 'meeting_scheduled', 'agent_call_requested', 'buy_action_initiated'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True) # e.g., "Product X interest", "Sales agent: John Doe"
    sales_agent_id = db.Column(db.String(36), nullable=True) # Optional: if you have agent IDs

    def __init__(self, conversation_id, user_id, company_id, event_type, details=None, sales_agent_id=None):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.company_id = company_id
        self.event_type = event_type
        self.details = details
        self.sales_agent_id = sales_agent_id

    def __repr__(self):
        return f'<ConversionEvent {self.event_type} Conv:{self.conversation_id}>'

class BotStatistic(db.Model):
    __tablename__ = 'bot_statistics'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Use UUID
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)
    
    # Metrics to track
    conversions = db.Column(db.Integer, default=0) # Number of conversions from leads
    
    # For response times, we'll store sum of times and count to calculate average
    total_user_response_time = db.Column(db.Float, default=0.0) # Sum of times it takes for users to respond to bot
    user_response_count = db.Column(db.Integer, default=0)     # Number of user responses measured

    num_recipients = db.Column(db.Integer, default=0)     # Number of unique recipients bot interacted with
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, company_id):
        self.company_id = company_id

    def __repr__(self):
        return f'<BotStatistic Company:{self.company_id}>'

    @property
    def average_user_response_time(self):
        if self.user_response_count > 0:
            return self.total_user_response_time / self.user_response_count
        return 0.0
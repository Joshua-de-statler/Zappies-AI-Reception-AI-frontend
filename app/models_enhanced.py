# app/models_enhanced.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

db = SQLAlchemy()

class User(db.Model):
    """Enhanced User model for mobile app authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(120))
    
    # Profile fields
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    
    # Authentication & Security
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    verification_code = db.Column(db.String(6))
    verification_expires = db.Column(db.DateTime)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    
    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # App-specific fields
    app_version = db.Column(db.String(20))
    device_token = db.Column(db.String(255))  # For push notifications
    platform = db.Column(db.String(20))  # iOS, Android, Web
    preferences = db.Column(JSONB, default={})
    
    # Referral system
    referral_code = db.Column(db.String(10), unique=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Subscription tier (for future monetization)
    subscription_tier = db.Column(db.String(20), default='free')
    subscription_expires = db.Column(db.DateTime)
    
    # Relationships
    wa_id = db.Column(db.String(50), unique=True)  # WhatsApp ID link
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    analytics_events = db.relationship('AnalyticsEvent', backref='user', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': str(self.uuid),
            'email': self.email,
            'phone': self.phone,
            'name': self.name,
            'company_name': self.company_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'industry': self.industry,
            'is_verified': self.is_verified,
            'subscription_tier': self.subscription_tier,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AnalyticsEvent(db.Model):
    """Track user interactions for analytics"""
    __tablename__ = 'analytics_events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    event_category = db.Column(db.String(50), index=True)
    event_data = db.Column(JSONB)
    
    # Context
    session_id = db.Column(UUID(as_uuid=True))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    platform = db.Column(db.String(20))
    app_version = db.Column(db.String(20))
    
    # Timing
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    duration_ms = db.Column(db.Integer)
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_analytics_user_timestamp', 'user_id', 'timestamp'),
        db.Index('idx_analytics_type_category', 'event_type', 'event_category'),
    )

class Notification(db.Model):
    """Push notifications management"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # chat, system, promotion, etc.
    
    # Delivery
    is_sent = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    
    # Additional data
    action_url = db.Column(db.String(255))
    data = db.Column(JSONB)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='notifications')

class AppSession(db.Model):
    """Track user app sessions for engagement metrics"""
    __tablename__ = 'app_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Session info
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    
    # Activity metrics
    messages_sent = db.Column(db.Integer, default=0)
    messages_received = db.Column(db.Integer, default=0)
    features_used = db.Column(JSONB, default=[])
    
    # Device info
    app_version = db.Column(db.String(20))
    device_model = db.Column(db.String(100))
    os_version = db.Column(db.String(50))
    
    # Relationship
    user = db.relationship('User', backref='sessions')

class FeatureUsage(db.Model):
    """Track feature adoption and usage"""
    __tablename__ = 'feature_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False, index=True)
    
    # Usage metrics
    first_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=1)
    
    # Feedback
    rating = db.Column(db.Integer)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'feature_name', name='_user_feature_uc'),
    )

class RevokedToken(db.Model):
    """Track revoked JWT tokens for security"""
    __tablename__ = 'revoked_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), unique=True, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
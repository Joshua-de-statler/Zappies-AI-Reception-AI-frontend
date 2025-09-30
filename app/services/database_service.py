# app/services/database_service.py
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models import db, Company, WhatsAppUser, Conversation, Message, ConversionEvent, BotStatistic

logger = logging.getLogger(__name__)

def _commit_session():
    """Commits the current database session with error handling."""
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database commit failed: {e}", exc_info=True)
        return False

def _add_and_commit(instance):
    """Adds a new instance to the database and commits it."""
    db.session.add(instance)
    if not _commit_session():
        logger.error(f"Failed to create {instance.__class__.__name__}.")
        return None
    return instance

def get_or_create_default_company():
    """Gets or creates the default company."""
    company = Company.query.filter_by(name="Default Company").first()
    if not company:
        company = _add_and_commit(Company(name="Default Company"))
        if company:
            logger.info("Created new default company.")
    return company

def get_or_create_whatsapp_user(wa_id: str, name: str, company_id: int):
    """Gets or creates a WhatsApp user."""
    user = WhatsAppUser.query.filter_by(wa_id=wa_id).first()
    if not user:
        user = _add_and_commit(WhatsAppUser(wa_id=wa_id, name=name, company_id=company_id))
        if user:
            logger.info(f"Created new WhatsApp user: {name} ({wa_id}).")
    return user

def get_or_create_conversation(user_id: int, company_id: int):
    """Gets or creates a conversation."""
    conversation = Conversation.query.filter_by(user_id=user_id, company_id=company_id).first()
    if not conversation:
        conversation = _add_and_commit(Conversation(user_id=user_id, company_id=company_id))
        if conversation:
            logger.info(f"Created new conversation for user {user_id}.")
    return conversation

def update_conversation_status(conversation_id: int, status: str):
    """Updates the status of a conversation."""
    conversation = Conversation.query.get(conversation_id)
    if conversation:
        conversation.status = status
        _commit_session()
    else:
        logger.warning(f"Conversation {conversation_id} not found for status update.")

def record_message(conversation_id: int, sender_type: str, content: str, response_to_message_id: int = None, meta_message_id: str = None):
    """
    Records an incoming (user) or outgoing (bot) message.
    For user messages with a meta_message_id, it handles unique constraint violations to prevent duplicates.
    Returns a tuple: (message_object, is_duplicate_bool). Returns (None, False) on unexpected error.
    """
    try:
        if meta_message_id and sender_type == 'user':
            existing_message = Message.query.filter_by(meta_message_id=meta_message_id).first()
            if existing_message:
                logger.warning(f"Meta message ID '{meta_message_id}' already exists. Skipping.")
                return (existing_message, True)

        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            response_to_message_id=response_to_message_id,
            timestamp=datetime.utcnow(),
            meta_message_id=meta_message_id
        )
        db.session.add(message)
        db.session.commit()
        logger.info(f"Recorded {sender_type} message for conversation {conversation_id}: '{content[:50]}...'")
        return (message, False)

    except IntegrityError:
        db.session.rollback()
        logger.warning(f"Duplicate message with meta_message_id '{meta_message_id}' received. Ignoring.")
        existing_message = Message.query.filter_by(meta_message_id=meta_message_id).first()
        return (existing_message, True)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error recording message for conversation {conversation_id}: {e}", exc_info=True)
        return (None, False)

def get_conversation_history_for_gemini(conversation_id: int):
    """Retrieves the conversation history for the Gemini model."""
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    history = []
    for msg in messages:
        role = "user" if msg.sender_type == "user" else "model"
        history.append({"role": role, "parts": [{"text": msg.content}]})
    return history

def record_conversion_event(conversation_id: int, event_type: str, details: dict = None):
    """Records a conversion event."""
    event = ConversionEvent(
        conversation_id=conversation_id,
        event_type=event_type,
        details=details,
        timestamp=datetime.utcnow()
    )
    _add_and_commit(event)
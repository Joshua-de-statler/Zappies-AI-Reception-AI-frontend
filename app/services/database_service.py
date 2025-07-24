import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models import db, Company, WhatsAppUser, Conversation, Message, ConversionEvent, BotStatistic

logger = logging.getLogger(__name__)

def commit_safely():
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database commit failed: {e}", exc_info=True)
        return False

def get_or_create_default_company():
    company = Company.query.filter_by(name="Default Company").first()
    if not company:
        company = Company(name="Default Company", api_key="default_key") # Placeholder API key
        db.session.add(company)
        if not commit_safely():
            logger.error("Failed to create default company.")
            return None
        logger.info("Created new default company.")
    return company

def get_or_create_whatsapp_user(wa_id: str, name: str, company_id: int):
    user = WhatsAppUser.query.filter_by(wa_id=wa_id).first()
    if not user:
        user = WhatsAppUser(wa_id=wa_id, name=name, company_id=company_id)
        db.session.add(user)
        if not commit_safely():
            logger.error(f"Failed to create WhatsApp user {wa_id}.")
            return None
        logger.info(f"Created new WhatsApp user: {name} ({wa_id}).")
    return user

def get_or_create_conversation(user_id: int, company_id: int):
    conversation = Conversation.query.filter_by(user_id=user_id, company_id=company_id).first()
    if not conversation:
        conversation = Conversation(user_id=user_id, company_id=company_id)
        db.session.add(conversation)
        if not commit_safely():
            logger.error(f"Failed to create conversation for user {user_id}.")
            return None
        logger.info(f"Created new conversation for user {user_id}.")
    return conversation

def update_conversation_status(conversation_id: int, status: str):
    conversation = Conversation.query.get(conversation_id)
    if conversation:
        conversation.status = status
        if not commit_safely():
            logger.error(f"Failed to update conversation {conversation_id} status to {status}.")
    else:
        logger.warning(f"Conversation {conversation_id} not found for status update.")

def record_message(conversation_id: int, sender_type: str, content: str, response_to_message_id: int = None, meta_message_id: str = None):
    """
    Records an incoming (user) or outgoing (bot) message.
    For user messages with a meta_message_id, it handles unique constraint violations to prevent duplicates.
    Returns a tuple: (message_object, is_duplicate_bool). Returns (None, False) on unexpected error.
    """
    try:
        # Handle user message deduplication
        if meta_message_id and sender_type == 'user':
            # First, check if it already exists (fast query for known duplicates or pre-existing data)
            existing_message = Message.query.filter_by(meta_message_id=meta_message_id).first()
            if existing_message:
                logger.warning(f"Meta message ID '{meta_message_id}' already exists in DB. Returning existing message.")
                return (existing_message, True) # Signal that it's a duplicate

            # If not found, attempt to add. IntegrityError will catch concurrent writes.
            message = Message(
                conversation_id=conversation_id,
                sender_type=sender_type,
                content=content,
                response_to_message_id=response_to_message_id,
                timestamp=datetime.utcnow(),
                meta_message_id=meta_message_id
            )
            db.session.add(message)
            # Flush to attempt write and potentially catch IntegrityError for concurrent requests
            # before the full commit and before expensive operations in whatsapp_utils.
            db.session.flush()

            if not commit_safely():
                logger.error(f"Failed to commit new user message for Meta ID '{meta_message_id}'.")
                return (None, False) # Failed to commit, treat as error

            logger.info(f"Recorded NEW user message for conversation {conversation_id}: '{content[:50]}...' (Meta ID: {meta_message_id})")
            return (message, False) # Successfully recorded new message

        # Handle bot messages or user messages without meta_message_id
        else:
            message = Message(
                conversation_id=conversation_id,
                sender_type=sender_type,
                content=content,
                response_to_message_id=response_to_message_id,
                timestamp=datetime.utcnow(),
                meta_message_id=meta_message_id # Will be None for bot messages
            )
            db.session.add(message)
            if not commit_safely():
                logger.error(f"Failed to save {sender_type} message for conversation '{conversation_id}'.")
                return (None, False)
            logger.info(f"Recorded {sender_type} message for conversation {conversation_id}: '{content[:50]}...'")
            return (message, False) # Successfully recorded, not a duplicate

    except IntegrityError as e:
        db.session.rollback() # Rollback the session if IntegrityError occurs
        if meta_message_id and sender_type == 'user' and "meta_message_id" in str(e):
            logger.warning(f"IntegrityError: Concurrent write for Meta message ID '{meta_message_id}' detected. It's a duplicate.")
            # Attempt to retrieve the message that *was* successfully written by another process
            existing_message = Message.query.filter_by(meta_message_id=meta_message_id).first()
            if existing_message:
                return (existing_message, True) # Indicate it's a duplicate
            else:
                logger.error(f"IntegrityError for {meta_message_id} but couldn't retrieve existing message. Possible race condition during retrieval.")
                return (None, False) # Fallback to error
        else:
            logger.error(f"IntegrityError: Unexpected database integrity error recording {sender_type} message for conversation ID '{conversation_id}': {e}", exc_info=True)
            return (None, False) # General integrity error

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: Error recording {sender_type} message for conversation ID '{conversation_id}': {e}", exc_info=True)
        db.session.rollback()
        return (None, False) # General SQLAlchemy error

def get_conversation_history_for_gemini(conversation_id: int):
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    history = []
    for msg in messages:
        role = "user" if msg.sender_type == "user" else "model"
        history.append({"role": role, "parts": [{"text": msg.content}]})
    return history

def record_conversion_event(conversation_id: int, event_type: str, details: dict = None):
    event = ConversionEvent(
        conversation_id=conversation_id,
        event_type=event_type,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.session.add(event)
    if not commit_safely():
        logger.error(f"Failed to record conversion event '{event_type}' for conversation {conversation_id}.")

def get_bot_statistic_for_company(company_id: int):
    stat = BotStatistic.query.filter_by(company_id=company_id).first()
    if not stat:
        stat = BotStatistic(company_id=company_id, total_conversions=0, total_response_time_ms=0, total_recipients=0)
        db.session.add(stat)
        if not commit_safely():
            logger.error(f"Failed to create bot statistic for company {company_id}.")
            return None
    return stat

def update_bot_statistic_conversions(company_id: int, increment: int = 1):
    stat = get_bot_statistic_for_company(company_id)
    if stat:
        stat.total_conversions += increment
        if not commit_safely():
            logger.error(f"Failed to update conversion statistic for company {company_id}.")

def update_bot_statistic_response_time(company_id: int, duration_ms: float):
    stat = get_bot_statistic_for_company(company_id)
    if stat:
        stat.total_response_time_ms += duration_ms
        if not commit_safely():
            logger.error(f"Failed to update response time statistic for company {company_id}.")

def update_bot_statistic_recipients(company_id: int, increment: int = 1):
    stat = get_bot_statistic_for_company(company_id)
    if stat:
        stat.total_recipients += increment
        if not commit_safely():
            logger.error(f"Failed to update recipient statistic for company {company_id}.")
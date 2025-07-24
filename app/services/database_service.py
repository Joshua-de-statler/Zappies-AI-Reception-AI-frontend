import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.models import db, Company, WhatsAppUser, Conversation, Message, ConversionEvent, BotStatistic # Ensure all models are imported

logger = logging.getLogger(__name__)

# --- Helper Function for Safe Commit ---
def commit_safely():
    """Commits the current session and handles exceptions, rolling back on failure."""
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback() # Rollback changes if commit fails
        logger.error(f"Database commit failed: {e}", exc_info=True)
        return False

# --- Company Operations ---
def get_or_create_company(name: str):
    """Gets an existing company by name or creates a new one."""
    try:
        company = Company.query.filter_by(name=name).first()
        if not company:
            company = Company(name=name, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            db.session.add(company)
            if not commit_safely():
                logger.error(f"Failed to save new company '{name}' after add.")
                return None # Return None if commit failed
            logger.info(f"Created new company: {name} (ID: {company.id})")
        return company
    except SQLAlchemyError as e:
        logger.error(f"Error getting or creating company '{name}': {e}", exc_info=True)
        db.session.rollback() # Rollback in case of query error
        return None

def get_or_create_default_company():
    """
    Convenience function to get or create the main company for the bot.
    You might adjust 'My Bot Company' to a more specific name if preferred.
    """
    return get_or_create_company(name="My Bot Company")

# --- WhatsApp User Operations ---
def get_or_create_whatsapp_user(wa_id: str, name: str, company_id: int):
    """Gets an existing WhatsApp user by WA ID and company_id or creates a new one."""
    try:
        user = WhatsAppUser.query.filter_by(wa_id=wa_id, company_id=company_id).first()
        if not user:
            user = WhatsAppUser(wa_id=wa_id, name=name, company_id=company_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            db.session.add(user)
            if not commit_safely():
                logger.error(f"Failed to save new WhatsApp user '{wa_id}' after add.")
                return None
            logger.info(f"Created new WhatsApp user: {name} ({wa_id}) (ID: {user.id})")
        else:
            # Optionally update user name if it has changed
            if user.name != name:
                user.name = name
                user.updated_at = datetime.utcnow()
                commit_safely() # Commit update to name/timestamp
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error getting or creating WhatsApp user '{wa_id}': {e}", exc_info=True)
        db.session.rollback()
        return None

# --- Conversation Operations ---
def get_or_create_conversation(user_id: int, company_id: int):
    """Gets the active conversation for a user within a company or creates a new one."""
    try:
        # Assuming one active conversation per user for simplicity.
        # If you need multiple simultaneous conversations, this logic would need expansion.
        conversation = Conversation.query.filter_by(user_id=user_id, company_id=company_id, status='active').first()
        if not conversation:
            conversation = Conversation(
                user_id=user_id,
                company_id=company_id,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status='active'
            )
            db.session.add(conversation)
            if not commit_safely():
                logger.error(f"Failed to save new conversation for user ID '{user_id}' after add.")
                return None
            logger.info(f"Created new conversation (ID: {conversation.id}) for user ID: {user_id}")
        else:
            # Update timestamp for existing active conversation
            conversation.updated_at = datetime.utcnow()
            commit_safely()
        return conversation
    except SQLAlchemyError as e:
        logger.error(f"Error getting or creating conversation for user ID '{user_id}': {e}", exc_info=True)
        db.session.rollback()
        return None

def update_conversation_status(conversation_id: int, status: str):
    """Updates the status of a conversation (e.g., 'active', 'closed')."""
    try:
        conversation = Conversation.query.get(conversation_id)
        if conversation:
            conversation.status = status
            conversation.updated_at = datetime.utcnow()
            if not commit_safely():
                return False
            logger.info(f"Updated conversation {conversation_id} status to '{status}'.")
            return True
        logger.warning(f"Conversation with ID {conversation_id} not found for status update.")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating conversation {conversation_id} status: {e}", exc_info=True)
        db.session.rollback()
        return False

# --- Deduplication Check (NEW FUNCTION) ---
def has_meta_message_id_been_processed(meta_message_id: str) -> bool:
    """
    Checks if a given Meta WhatsApp message ID has already been recorded in the database.
    This prevents reprocessing of duplicate webhooks.
    """
    if not meta_message_id:
        return False # Cannot deduplicate if no ID is provided

    try:
        # Check if any message with this meta_message_id exists.
        # Only user messages will carry the original meta_message_id from Meta.
        return Message.query.filter_by(meta_message_id=meta_message_id).first() is not None
    except SQLAlchemyError as e:
        logger.error(f"Database error checking for duplicate Meta message ID {meta_message_id}: {e}", exc_info=True)
        db.session.rollback() # Rollback if query fails
        # In case of DB error, assume it's not processed to avoid missing messages,
        # but this might lead to duplicates if the error is transient.
        return False


# --- Message Operations (MODIFIED record_message) ---
def record_message(conversation_id: int, sender_type: str, content: str, response_to_message_id: int = None, meta_message_id: str = None):
    """Records an incoming (user) or outgoing (bot) message, including Meta's message ID."""
    try:
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type, # Expected: 'user' or 'bot'
            content=content,
            response_to_message_id=response_to_message_id, # Links bot response to user's message
            timestamp=datetime.utcnow(),
            meta_message_id=meta_message_id # Store Meta's ID here (will be None for bot messages)
        )
        db.session.add(message)
        if not commit_safely():
            logger.error(f"Failed to save {sender_type} message for conversation '{conversation_id}' after add.")
            return None
        logger.info(f"Recorded {sender_type} message for conversation {conversation_id}: '{content[:50]}...' (Meta ID: {meta_message_id if meta_message_id else 'N/A'})")
        return message
    except SQLAlchemyError as e:
        logger.error(f"Error recording {sender_type} message for conversation ID '{conversation_id}': {e}", exc_info=True)
        db.session.rollback()
        return None

def get_conversation_history_for_gemini(conversation_id: int) -> list:
    """
    Retrieves messages for a given conversation and formats them
    into a list of dictionaries suitable for Gemini's chat history.
    Gemini expects roles 'user' and 'model'.
    """
    history = []
    try:
        # Query messages for the conversation, ordered by timestamp
        messages = Message.query.filter_by(conversation_id=conversation_id)\
                                .order_by(Message.timestamp.asc())\
                                .all()
        for msg in messages:
            # Map our sender_type to Gemini's expected role ('user' or 'model')
            gemini_role = 'user' if msg.sender_type == 'user' else 'model'
            history.append({'role': gemini_role, 'parts': [msg.content]})
        logger.debug(f"Fetched {len(history)} messages for conversation {conversation_id} for Gemini history.")
    except SQLAlchemyError as e:
        logger.error(f"Error fetching conversation history for Gemini (conversation ID: {conversation_id}): {e}", exc_info=True)
        db.session.rollback() # Rollback if error occurred during query
        return [] # Return empty history on error, so generate_response doesn't fail
    return history

# --- Conversion Event Operations ---
def record_conversion_event(conversation_id: int, event_type: str, details: dict = None):
    """Records a specific conversion event within a conversation."""
    try:
        event = ConversionEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            details=details, # This column is JSON, so dicts are fine
            timestamp=datetime.utcnow()
        )
        db.session.add(event)
        if not commit_safely():
            logger.error(f"Failed to save conversion event '{event_type}' for conversation '{conversation_id}'.")
            return None
        logger.info(f"Recorded conversion event '{event_type}' for conversation {conversation_id}.")
        return event
    except SQLAlchemyError as e:
        logger.error(f"Error recording conversion event for conversation {conversation_id}: {e}", exc_info=True)
        db.session.rollback()
        return None

# --- Bot Statistics Operations ---
def get_bot_statistic_for_company(company_id: int):
    """Retrieves or initializes bot statistics for a given company."""
    try:
        stats = BotStatistic.query.filter_by(company_id=company_id).first()
        if not stats:
            stats = BotStatistic(company_id=company_id, total_messages=0, total_recipients=0, total_conversions=0, avg_response_time_ms=0, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            db.session.add(stats)
            commit_safely()
            logger.info(f"Initialized bot statistics for company ID: {company_id}.")
        return stats
    except SQLAlchemyError as e:
        logger.error(f"Error getting or creating bot statistics for company {company_id}: {e}", exc_info=True)
        db.session.rollback()
        return None

def update_bot_statistic_conversions(company_id: int):
    """Increments the total conversions count for a company's bot statistics."""
    try:
        stats = get_bot_statistic_for_company(company_id)
        if stats:
            stats.total_conversions += 1
            stats.updated_at = datetime.utcnow()
            commit_safely()
            logger.info(f"Updated bot statistics: conversions for company {company_id}.")
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating bot statistics conversions for company {company_id}: {e}", exc_info=True)
        db.session.rollback()
        return False

def update_bot_statistic_response_time(company_id: int, response_time_ms: float):
    """Updates the average response time for a company's bot statistics."""
    try:
        stats = get_bot_statistic_for_company(company_id)
        if stats:
            # Simple average update (consider a more robust rolling average for production)
            current_total_time = stats.avg_response_time_ms * stats.total_messages
            stats.total_messages += 1 # Assuming a message is responded to
            stats.avg_response_time_ms = (current_total_time + response_time_ms) / stats.total_messages if stats.total_messages > 0 else response_time_ms
            stats.updated_at = datetime.utcnow()
            commit_safely()
            logger.info(f"Updated bot statistics: response time for company {company_id}.")
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating bot statistics response time for company {company_id}: {e}", exc_info=True)
        db.session.rollback()
        return False

def update_bot_statistic_recipients(company_id: int):
    """Increments the total unique recipients count for a company's bot statistics."""
    try:
        stats = get_bot_statistic_for_company(company_id)
        if stats:
            stats.total_recipients += 1 # This should be called only for *new* unique recipients
            stats.updated_at = datetime.utcnow()
            commit_safely()
            logger.info(f"Updated bot statistics: recipients for company {company_id}.")
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating bot statistics recipients for company {company_id}: {e}", exc_info=True)
        db.session.rollback()
        return False
# app/services/database_service.py

from app.models import db, Company, WhatsappUser, Conversation, Message, BotStatistic, ConversionEvent
from datetime import datetime, timedelta
import logging

# --- Company Management ---
def get_or_create_company(company_name="Zappies AI Default"):
    """
    Retrieves a company by name or creates it if it doesn't exist.
    For now, we'll use a default company name.
    """
    company = Company.query.filter_by(name=company_name).first()
    if not company:
        company = Company(name=company_name)
        db.session.add(company)
        db.session.commit()
        logging.info(f"Created new company: {company.name} with ID: {company.id}")
    return company

# --- User and Conversation Management ---
def get_or_create_whatsapp_user(wa_id, name, company_id):
    """
    Retrieves a WhatsApp user by wa_id or creates them if they don't exist.
    Updates last_interaction_at if user exists.
    """
    user = WhatsappUser.query.filter_by(wa_id=wa_id).first()
    if not user:
        user = WhatsappUser(wa_id=wa_id, company_id=company_id, name=name)
        db.session.add(user)
        db.session.commit()
        logging.info(f"Created new WhatsApp user: {name} ({wa_id})")
        # Also increment num_recipients for the company
        update_bot_statistics(company_id, new_recipient=True)
    else:
        # Update last interaction time
        user.last_interaction_at = datetime.utcnow()
        db.session.commit()
    return user

def get_or_create_conversation(user_id, company_id):
    """
    Retrieves the most recent active conversation for a user, or creates a new one.
    A conversation is considered active if it hasn't been explicitly closed.
    For simplicity, we'll assume a conversation is active if its end_time is NULL.
    In a real app, you might have a more complex logic (e.g., timeout after X minutes of inactivity).
    """
    conversation = Conversation.query.filter_by(user_id=user_id, company_id=company_id, status='active') \
                                     .order_by(Conversation.start_time.desc()).first()
    if not conversation:
        conversation = Conversation(user_id=user_id, company_id=company_id)
        db.session.add(conversation)
        db.session.commit()
        logging.info(f"Created new conversation for user {user_id}")
    return conversation

def record_message(conversation_id, sender_type, content, response_to_message_id=None):
    """
    Records a message in the database.
    """
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=content,
        response_to_message_id=response_to_message_id
    )
    db.session.add(message)
    db.session.commit()
    logging.info(f"Recorded message from {sender_type} in conversation {conversation_id}")
    return message

# --- Statistics Tracking ---
def update_bot_statistics(company_id, conversions_delta=0, user_response_time_delta=0.0, is_user_response=False, new_recipient=False):
    """
    Updates the aggregate bot statistics for a given company.
    """
    stats = BotStatistic.query.filter_by(company_id=company_id).first()
    if not stats:
        stats = BotStatistic(company_id=company_id)
        db.session.add(stats)
        db.session.commit()
        logging.info(f"Created new BotStatistic entry for company {company_id}")

    stats.conversions += conversions_delta
    
    if is_user_response:
        stats.total_user_response_time += user_response_time_delta
        stats.user_response_count += 1
    
    if new_recipient:
        stats.num_recipients += 1
    
    db.session.commit()
    logging.info(f"Updated bot statistics for company {company_id}")

def record_conversion_event(conversation_id, user_id, company_id, event_type, details=None, sales_agent_id=None):
    """
    Records a specific conversion event.
    """
    event = ConversionEvent(
        conversation_id=conversation_id,
        user_id=user_id,
        company_id=company_id,
        event_type=event_type,
        details=details,
        sales_agent_id=sales_agent_id
    )
    db.session.add(event)
    db.session.commit()
    logging.info(f"Recorded conversion event: {event_type} for conversation {conversation_id}")
    # Also update aggregate conversion count
    # You might want to be more nuanced here based on your conversion definition
    # For now, every conversion event increments the aggregate.
    update_bot_statistics(company_id, conversions_delta=1)

def calculate_and_update_response_time(bot_message_id, user_message_timestamp, company_id):
    """
    Calculates the time taken for a user to respond to a specific bot message
    and updates the overall bot statistics.
    """
    bot_message = Message.query.get(bot_message_id)
    if bot_message and bot_message.sender_type == 'bot':
        response_time_seconds = (user_message_timestamp - bot_message.timestamp).total_seconds()
        if response_time_seconds > 0: # Only count positive response times
            update_bot_statistics(company_id, user_response_time_delta=response_time_seconds, is_user_response=True)
            logging.info(f"Calculated user response time: {response_time_seconds:.2f}s")
    else:
        logging.warning(f"Could not find bot message with ID {bot_message_id} or it was not sent by bot.")
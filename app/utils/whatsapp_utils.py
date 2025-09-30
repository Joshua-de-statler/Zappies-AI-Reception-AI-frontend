# app/utils/whatsapp_utils.py

import logging
import json
import requests
import os
import time
from datetime import datetime

from flask import current_app

from app.services.database_service import (
    get_or_create_default_company,
    get_or_create_whatsapp_user,
    get_or_create_conversation,
    record_message,
    record_conversion_event
)
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# --- AI Service Initialization ---
gemini_service = None
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize GeminiService: {e}. AI features will be limited.", exc_info=True)

# --- Intent Detection Keywords for Human Handover ---
MEETING_KEYWORDS = [
    "schedule meeting", "book a meeting", "talk to sales",
    "book a call", "want the product", "yes", "i'm interested",
    "book now", "meeting", "sales"
]

# --- Utility Functions ---

def get_whatsapp_message_type(data: dict) -> str:
    """Determines the type of WhatsApp message received."""
    if not isinstance(data, dict):
        return "unsupported"
    
    try:
        return data['entry'][0]['changes'][0]['value']['messages'][0]['type']
    except (KeyError, IndexError):
        try:
            if 'statuses' in data['entry'][0]['changes'][0]['value']:
                return "status"
        except (KeyError, IndexError):
            return "unsupported"
    return "unsupported"

def get_media_url(media_id: str):
    """Retrieves a temporary URL for a media file."""
    url = f"{current_app.config['GRAPH_API_URL']}/{media_id}"
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("url")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching media URL for ID {media_id}: {e}", exc_info=True)
        return None

def download_media(media_url: str):
    """Downloads media content from a given URL."""
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    try:
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading media from URL {media_url}: {e}", exc_info=True)
        return None

def send_whatsapp_message(phone_number_id: str, to_number: str, text_message: str):
    """Sends a text message to a WhatsApp user."""
    if not current_app.config['ACCESS_TOKEN'] or not phone_number_id:
        logger.error("ACCESS_TOKEN or PHONE_NUMBER_ID is not set.")
        return False

    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_message},
    }
    url = f"{current_app.config['GRAPH_API_URL']}/{phone_number_id}/messages"
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"WhatsApp message sent successfully to {to_number}.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending WhatsApp message to {to_number}: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"WhatsApp API Response: {e.response.text}")
        return False

def process_whatsapp_message(data):
    """Processes incoming WhatsApp webhook data."""
    ai_enabled = gemini_service and gemini_service.model is not None
    if not ai_enabled:
        logger.warning("GeminiService not initialized. AI responses will be unavailable.")

    message_type = get_whatsapp_message_type(data)

    if message_type == "status":
        logger.info("Received a WhatsApp message status update.")
        return "Status update acknowledged", 200
    elif message_type == "unsupported":
        logger.warning("Unsupported or invalid WhatsApp message structure received.")
        return "Unsupported message type", 400
    
    # Process 'message' types
    try:
        message = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_number = message['from']
        user_name = data['entry'][0]['changes'][0]['value']['contacts'][0]['profile']['name']
        meta_message_id = message['id']
        phone_number_id_for_sending = data['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']

        logger.info(f"Received incoming message from {user_name} ({from_number}) of type '{message['type']}'")
        
        # --- Database Operations ---
        company = get_or_create_default_company()
        if not company:
            return "Database company error", 500
        
        user = get_or_create_whatsapp_user(from_number, user_name, company.id)
        if not user:
            return "Database user error", 500

        conversation = get_or_create_conversation(user.id, company.id)
        if not conversation:
            return "Database conversation error", 500

        # --- Message Processing ---
        message_content = None
        ai_input_parts = []

        if message['type'] == 'text':
            message_body = message['text']['body']
            message_content = message_body
            ai_input_parts.append({"text": message_body})
            
            user_message_lower = message_body.lower()
            if any(keyword in user_message_lower for keyword in MEETING_KEYWORDS):
                if not current_app.config['CALENDLY_LINK']:
                    bot_response_text = "I can help schedule a meeting, but the booking link is not configured. Please contact support."
                    logger.error("CALENDLY_LINK is not set.")
                else:
                    bot_response_text = (
                        f"Great! To schedule a meeting, please use this link: {current_app.config['CALENDLY_LINK']}\n\n"
                        f"Our team looks forward to speaking with you!"
                    )
                    record_conversion_event(conversation.id, "meeting_scheduled_calendly", {"user_intent": message_body})
                
                logger.info(f"Handover triggered. Providing Calendly link.")
                recorded_user_message, is_duplicate = record_message(conversation.id, "user", message_content, meta_message_id=meta_message_id)
                if not is_duplicate and recorded_user_message:
                    record_message(conversation.id, "bot", bot_response_text, response_to_message_id=recorded_user_message.id)
                    send_whatsapp_message(phone_number_id_for_sending, from_number, bot_response_text)
                return "Handover message processed", 200

        # --- AI Response Generation ---
        recorded_user_message, is_duplicate = record_message(conversation.id, "user", message_content, meta_message_id=meta_message_id)
        if is_duplicate:
            return "Message already processed", 200
        if not recorded_user_message:
            return "Failed to record message", 500

        bot_response_text = "I apologize, but I'm currently unable to process your request."
        if ai_enabled and ai_input_parts:
            bot_response_text = gemini_service.generate_response(ai_input_parts, conversation.id)
        
        record_message(conversation.id, "bot", bot_response_text, response_to_message_id=recorded_user_message.id)
        send_whatsapp_message(phone_number_id_for_sending, from_number, bot_response_text)
        
        return "Message processed", 200

    except (IndexError, KeyError) as e:
        logger.error(f"Error parsing webhook data: {e}", exc_info=True)
        return "Invalid data format", 400
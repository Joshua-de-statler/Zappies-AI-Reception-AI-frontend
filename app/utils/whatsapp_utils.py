# app/utils/whatsapp_utils.py

import logging
import json
import requests
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

from app.services.gemini_service import GeminiService
from app.services.database_service import (
    get_or_create_default_company,
    get_or_create_whatsapp_user,
    get_or_create_conversation,
    record_message
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
GRAPH_API_URL = os.getenv("GRAPH_API_URL")

# Initialize GeminiService instance globally
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize GeminiService: {e}. AI features will be limited.")
    gemini_service = None

def get_whatsapp_message_type(data: dict) -> str:
    if not isinstance(data, dict):
        return "unsupported"

    if 'object' in data and 'entry' in data:
        for entry in data['entry']:
            if 'changes' in entry:
                for change in entry['changes']:
                    if 'value' in change:
                        if 'messages' in change['value']:
                            for message in change['value']['messages']:
                                if 'type' in message and message['type'] in ['text', 'button', 'reaction', 'interactive', 'image', 'video', 'audio', 'document']:
                                    return "message"
                        elif 'statuses' in change['value']:
                            return "status"
    return "unsupported"

def send_whatsapp_message(phone_number_id: str, to_number: str, text_message: str):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_message},
    }
    try:
        response = requests.post(
            f"{GRAPH_API_URL}/{phone_number_id}/messages", headers=headers, json=payload
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        logger.info(f"WhatsApp message sent successfully to {to_number}. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending WhatsApp message to {to_number}: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"WhatsApp API Response: {e.response.text}")
        return False

def process_whatsapp_message(data):
    ai_enabled = True
    if not gemini_service:
        logger.warning("GeminiService not initialized. AI responses will be unavailable.")
        ai_enabled = False

    message_type = get_whatsapp_message_type(data)

    if message_type == "status":
        logger.info(f"[{time.time()}] Received a WhatsApp message status update (e.g., sent, delivered, read). Acknowledging.")
        return "Status update acknowledged", 200
    elif message_type == "unsupported":
        logger.warning(f"[{time.time()}] Unsupported or invalid WhatsApp message structure received. Skipping processing.")
        return "Unsupported message type", 400

    for entry in data['entry']:
        for change in entry['changes']:
            if 'messages' in change['value']:
                for message in change['value']['messages']:
                    if message['type'] == 'text':
                        from_number = message['from']
                        user_name = change['value']['contacts'][0]['profile']['name']
                        message_body = message['text']['body']
                        meta_message_id = message['id'] # Get Meta's unique message ID

                        logger.info(f"[{time.time()}] Received incoming text message from {user_name} ({from_number}): '{message_body}' (Meta ID: {meta_message_id})")

                        # --- INITIAL SETUP FOR DB ENTRIES ---
                        company = get_or_create_default_company()
                        if not company:
                            logger.error(f"[{time.time()}] Failed to get or create default company. Cannot process message.")
                            # Consider sending an error message to user here, or just let Meta retry
                            return "Database company error", 500
                        company_id = company.id

                        user = get_or_create_whatsapp_user(from_number, user_name, company_id)
                        if not user:
                            logger.error(f"[{time.time()}] Failed to get or create WhatsApp user {from_number}. Cannot process message.")
                            return "Database user error", 500
                        user_id = user.id

                        conversation = get_or_create_conversation(user_id, company_id)
                        if not conversation:
                            logger.error(f"[{time.time()}] Failed to get or create conversation for user {user_id}. Cannot process message.")
                            return "Database conversation error", 500
                        conversation_id = conversation.id
                        # --- END INITIAL SETUP ---

                        # --- ATTEMPT TO RECORD USER MESSAGE (DEDUPLICATION POINT) ---
                        start_record_user_time = time.time()
                        recorded_user_message, is_duplicate = record_message(conversation_id, "user", message_body, meta_message_id=meta_message_id)
                        end_record_user_time = time.time()
                        logger.info(f"[{time.time()}] record_message for user (Meta ID {meta_message_id}) took {(end_record_user_time - start_record_user_time)*1000:.2f} ms. Is duplicate: {is_duplicate}")

                        if recorded_user_message is None:
                            logger.error(f"[{time.time()}] Failed to record user message (Meta ID {meta_message_id}). Skipping processing.")
                            return "Failed to record message", 500 # Return 500 if DB record failed, Meta will retry

                        if is_duplicate:
                            logger.info(f"[{time.time()}] Meta Message ID {meta_message_id} was identified as a duplicate. Skipping further processing and responding with 200 OK.")
                            return "Message already processed", 200 # Crucial: immediately return 200 OK
                        # --- END DEDUPLICATION ---

                        # If we reach here, it's a new, successfully recorded user message. Proceed with AI and sending.
                        logger.info(f"[{time.time()}] Proceeding with AI for new message (Meta ID: {meta_message_id}).")

                        ai_response_text = ""
                        if ai_enabled:
                            start_ai_time = time.time()
                            ai_response_text = gemini_service.generate_response(message_body)
                            end_ai_time = time.time()
                            logger.info(f"[{time.time()}] Gemini response took {(end_ai_time - start_ai_time)*1000:.2f} ms.")
                        else:
                            ai_response_text = "I apologize, but my AI is currently offline. I cannot process your request."
                            logger.warning(f"[{time.time()}] AI is offline, sending fallback response.")

                        record_bot_message_start_time = time.time()
                        record_message(conversation_id, "bot", ai_response_text, response_to_message_id=recorded_user_message.id)
                        record_bot_message_end_time = time.time()
                        logger.info(f"[{time.time()}] record_message for bot took {(record_bot_message_end_time - record_bot_message_start_time)*1000:.2f} ms.")

                        send_whatsapp_start_time = time.time()
                        phone_number_id_for_sending = change['value']['metadata']['phone_number_id']
                        send_whatsapp_message(phone_number_id_for_sending, from_number, ai_response_text)
                        send_whatsapp_end_time = time.time()
                        logger.info(f"[{time.time()}] send_whatsapp_message took {(send_whatsapp_end_time - send_whatsapp_start_time)*1000:.2f} ms. Successfully sent AI response to {from_number}.")

                        return "Message processed", 200

                    else:
                        logger.info(f"[{time.time()}] Received unsupported message type: {message.get('type')}. Skipping processing for now.")

            elif 'statuses' in change['value']:
                logger.info(f"[{time.time()}] Received a WhatsApp message status update. Acknowledging.")
                return "Status update acknowledged", 200

    return "Message processed", 200
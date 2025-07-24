# app/utils/whatsapp_utils.py

import logging
import json
import requests
import os
from dotenv import load_dotenv

from app.services.gemini_service import GeminiService
from app.services.database_service import (
    get_or_create_default_company,
    get_or_create_whatsapp_user,
    get_or_create_conversation,
    record_message,
    has_meta_message_id_been_processed # NEW IMPORT for deduplication check
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

# --- Message Deduplication (REMOVED IN-MEMORY SET) ---
# processed_message_ids = set()
# def is_message_processed(message_id: str) -> bool:
#     return message_id in processed_message_ids
# def add_message_to_processed_list(message_id: str):
#     processed_message_ids.add(message_id)
# --- END REMOVED ---

# --- Function to validate incoming WhatsApp messages ---
def get_whatsapp_message_type(data: dict) -> str:
    """
    Determines the type of incoming webhook data from WhatsApp.
    Returns "message", "status", or "unsupported".
    """
    if not isinstance(data, dict):
        return "unsupported"

    if 'object' in data and 'entry' in data:
        for entry in data['entry']:
            if 'changes' in entry:
                for change in entry['changes']:
                    if 'value' in change:
                        if 'messages' in change['value']:
                            for message in change['value']['messages']:
                                # Check for common message types we handle (e.g., 'text', 'button', 'reaction', etc.)
                                if 'type' in message and message['type'] in ['text', 'button', 'reaction', 'interactive', 'image', 'video', 'audio', 'document']:
                                    return "message" # Found a valid incoming user message
                        elif 'statuses' in change['value']:
                            return "status" # Found a status update

    return "unsupported"

def process_whatsapp_message(data):
    ai_enabled = True
    if not gemini_service:
        logger.warning("GeminiService not initialized. AI responses will be unavailable.")
        ai_enabled = False

    message_type = get_whatsapp_message_type(data)

    if message_type == "status":
        logger.info("Received a WhatsApp message status update (e.g., sent, delivered, read). Acknowledging.")
        return "Status update acknowledged", 200
    elif message_type == "unsupported":
        logger.warning("Unsupported or invalid WhatsApp message structure received. Skipping processing.")
        return "Unsupported message type", 400
    
    # If message_type is "message", proceed with the original logic for incoming messages
    for entry in data['entry']:
        for change in entry['changes']:
            if 'messages' in change['value']: # This check is still useful inside the loop
                for message in change['value']['messages']:
                    # Ensure we only process 'text' messages here, others are already filtered by get_whatsapp_message_type
                    # This internal check provides redundancy and clarity.
                    if message['type'] == 'text': 
                        from_number = message['from']
                        user_name = change['value']['contacts'][0]['profile']['name']
                        message_body = message['text']['body']
                        meta_message_id = message['id'] # Get Meta's unique message ID

                        logger.info(f"Processing incoming text message from {user_name} ({from_number}): '{message_body}' (Meta ID: {meta_message_id})")

                        # --- DATABASE-BASED DEDUPLICATION CHECK (NEW) ---
                        if has_meta_message_id_been_processed(meta_message_id):
                            logger.info(f"Meta Message ID {meta_message_id} already processed. Skipping.")
                            return "Message already processed", 200
                        # --- END NEW ---

                        company = get_or_create_default_company()
                        if not company:
                            logger.error("Failed to get or create default company. Cannot process message.")
                            send_whatsapp_message(
                                change['value']['metadata']['phone_number_id'],
                                from_number,
                                "I'm sorry, there was a problem with our system. Please try again later."
                            )
                            return "Database company error", 500
                        company_id = company.id

                        user = get_or_create_whatsapp_user(from_number, user_name, company_id)
                        if not user:
                            logger.error(f"Failed to get or create WhatsApp user {from_number}. Cannot process message.")
                            send_whatsapp_message(
                                change['value']['metadata']['phone_number_id'],
                                from_number,
                                "I'm sorry, there was a problem with our system. Please try again later."
                            )
                            return "Database user error", 500
                        user_id = user.id

                        conversation = get_or_create_conversation(user_id, company_id)
                        if not conversation:
                            logger.error(f"Failed to get or create conversation for user {user_id}. Cannot process message.")
                            send_whatsapp_message(
                                change['value']['metadata']['phone_number_id'],
                                from_number,
                                "I'm sorry, there was a problem with our system. Please try again later."
                            )
                            return "Database conversation error", 500
                        conversation_id = conversation.id

                        # Pass meta_message_id to record_message for user messages
                        record_message(conversation_id, "user", message_body, meta_message_id=meta_message_id)
                        logger.info(f"Recorded user message for conversation {conversation_id}: '{message_body}' with Meta ID: {meta_message_id}")

                        ai_response_text = ""
                        if ai_enabled:
                            ai_response_text = gemini_service.generate_response(message_body)
                        else:
                            ai_response_text = "I apologize, but my AI is currently offline. I cannot process your request."
                            logger.warning("AI is offline, sending fallback response.")

                        # For bot messages, meta_message_id will be None
                        record_message(conversation_id, "bot", ai_response_text)
                        logger.info(f"Recorded bot message for conversation {conversation_id}: '{ai_response_text}'")

                        phone_number_id_for_sending = change['value']['metadata']['phone_number_id']
                        send_whatsapp_message(phone_number_id_for_sending, from_number, ai_response_text)
                        logger.info(f"Successfully sent AI response to {from_number}.")

                        # Removed add_message_to_processed_list as deduplication is now DB-based
                        # add_message_to_processed_list(message_id)
                        # logger.info(f"Marked message ID as processed: {message_id}")

                    else:
                        logger.info(f"Received unsupported message type: {message.get('type')}. Skipping processing for now.")

            elif 'statuses' in change['value']:
                logger.info("Received a WhatsApp message status update (e.g., delivered/read) within main loop. This should have been caught earlier. Acknowledging anyway.")
                return "Status update acknowledged (redundant check)", 200 # Redundant but safe

    return "Message processed", 200 # Default return if for loop finishes without returning


def send_whatsapp_message(phone_number_id, to_number, text_message):
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
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"

    response_json = None
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Message sent to {to_number}: '{text_message}'")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message to {to_number}: {e}")
        if e.response is not None:
            logger.error(f"Response content: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending message: {e}")

    return response_json
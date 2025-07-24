# app/utils/whatsapp_utils.py

import logging
import json
import requests
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv # Ensure this import is at the top for load_dotenv()

# Import necessary database service functions
from app.services.database_service import (
    get_or_create_default_company,
    get_or_create_whatsapp_user,
    get_or_create_conversation,
    record_message,
    record_conversion_event # Added for logging handover events
)
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Load environment variables.
# It's good practice to ensure they're loaded, though run.py or config.py might also do this.
# This ensures that variables like ACCESS_TOKEN and CALENDLY_LINK are available here.
load_dotenv()

# --- Configuration from Environment Variables ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
GRAPH_API_URL = os.getenv("GRAPH_API_URL", "https://graph.facebook.com") # Default to stable Graph API URL
CALENDLY_LINK = os.getenv("CALENDLY_LINK") # Your Calendly booking link

# --- AI Service Initialization ---
gemini_service = None
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize GeminiService: {e}. AI features will be limited.", exc_info=True)

# --- Intent Detection Keywords for Human Handover ---
# These keywords will trigger the Calendly link response.
# Expand or refine this list based on common user phrases.
MEETING_KEYWORDS = [
    "schedule meeting", "book a meeting", "talk to sales",
    "book a call", "want the product", "yes", "i'm interested",
    "book now", "meeting", "sales" # Added more common keywords
]

# --- Utility Functions ---

def get_whatsapp_message_type(data: dict) -> str:
    """
    Determines the type of WhatsApp message received (e.g., 'message', 'status', 'unsupported').
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
                                if 'type' in message and message['type'] in ['text', 'button', 'reaction', 'interactive', 'image', 'video', 'audio', 'document', 'sticker', 'location', 'contacts', 'order', 'system', 'unknown']:
                                    return "message"
                        elif 'statuses' in change['value']:
                            return "status"
    return "unsupported"

def send_whatsapp_message(phone_number_id: str, to_number: str, text_message: str):
    """
    Sends a text message to a WhatsApp user via the WhatsApp Business API.
    """
    if not ACCESS_TOKEN:
        logger.error("ACCESS_TOKEN is not set. Cannot send WhatsApp message.")
        return False
    if not phone_number_id:
        logger.error("PHONE_NUMBER_ID is missing. Cannot send WhatsApp message.")
        return False

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
    """
    Processes incoming WhatsApp webhook data, handles messages, and triggers responses.
    This function now includes human handover logic for meeting scheduling.
    """
    ai_enabled = True
    if not gemini_service or gemini_service.model is None: # Check if model was initialized successfully
        logger.warning("GeminiService not initialized or model not available. AI responses will be unavailable.")
        ai_enabled = False

    message_type = get_whatsapp_message_type(data)

    if message_type == "status":
        logger.info(f"[{time.time()}] Received a WhatsApp message status update (e.g., sent, delivered, read). Acknowledging.")
        return "Status update acknowledged", 200
    elif message_type == "unsupported":
        logger.warning(f"[{time.time()}] Unsupported or invalid WhatsApp message structure received. Skipping processing.")
        return "Unsupported message type", 400
    
    # Process 'message' type (actual incoming messages)
    for entry in data['entry']:
        for change in entry['changes']:
            if 'messages' in change['value']:
                for message in change['value']['messages']:
                    # Only process text messages for now
                    if message['type'] == 'text':
                        from_number = message['from'] # User's WhatsApp ID (phone number)
                        user_name = change['value']['contacts'][0]['profile']['name'] # User's name
                        message_body = message['text']['body'] # Actual text content
                        meta_message_id = message['id'] # Meta's unique message ID for deduplication

                        logger.info(f"[{time.time()}] Received incoming text message from {user_name} ({from_number}): '{message_body}' (Meta ID: {meta_message_id})")

                        # --- Database Setup (Get or Create User, Company, Conversation) ---
                        company = get_or_create_default_company()
                        if not company:
                            logger.error(f"[{time.time()}] Failed to get or create default company. Cannot process message.")
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
                        # --- End Database Setup ---

                        # --- Record User Message & Deduplicate ---
                        start_record_user_time = time.time()
                        # Pass meta_message_id for deduplication
                        recorded_user_message, is_duplicate = record_message(conversation_id, "user", message_body, meta_message_id=meta_message_id)
                        end_record_user_time = time.time()
                        logger.info(f"[{time.time()}] record_message for user (Meta ID {meta_message_id}) took {(end_record_user_time - start_record_user_time)*1000:.2f} ms. Is duplicate: {is_duplicate}")

                        if recorded_user_message is None:
                            logger.error(f"[{time.time()}] Failed to record user message (Meta ID {meta_message_id}). Skipping processing.")
                            return "Failed to record message", 500

                        if is_duplicate:
                            logger.info(f"[{time.time()}] Meta Message ID {meta_message_id} was identified as a duplicate. Skipping further processing and responding with 200 OK.")
                            return "Message already processed", 200
                        # --- End Deduplication ---

                        # --- HUMAN HANDOVER LOGIC (Calendly Integration) ---
                        user_message_lower = message_body.lower()
                        handover_triggered = False
                        bot_response_text = "" # Initialize bot_response_text

                        for keyword in MEETING_KEYWORDS:
                            if keyword in user_message_lower:
                                if not CALENDLY_LINK:
                                    logger.error("CALENDLY_LINK environment variable is not set. Cannot provide booking link.")
                                    bot_response_text = "I understand you'd like to schedule a meeting. However, I'm currently unable to provide a booking link. Please try again later or contact support directly."
                                else:
                                    bot_response_text = (
                                        f"Great! I can help you schedule a meeting with one of our sales consultants.\n\n"
                                        f"Please use this link to book a time that works best for you:\n{CALENDLY_LINK}\n\n"
                                        f"Our team looks forward to speaking with you!"
                                    )
                                    # Record the conversion event for handover
                                    record_conversion_event(
                                        conversation_id,
                                        "meeting_scheduled_calendly",
                                        {"user_intent": message_body, "calendly_link_provided": CALENDLY_LINK}
                                    )
                                logger.info(f"[{time.time()}] Handover triggered by keyword: '{keyword}'. Providing Calendly link.")
                                handover_triggered = True
                                break # Exit loop once a keyword is matched

                        # --- Proceed with AI if handover not triggered ---
                        if not handover_triggered:
                            logger.info(f"[{time.time()}] Proceeding with AI for new message (Meta ID: {meta_message_id}).")
                            
                            if ai_enabled:
                                start_ai_time = time.time()
                                # Call GeminiService to generate response, passing conversation_id for context
                                ai_response_text = gemini_service.generate_response(message_body, conversation_id)
                                end_ai_time = time.time()
                                logger.info(f"[{time.time()}] Gemini response took {(end_ai_time - start_ai_time)*1000:.2f} ms.")
                            else:
                                ai_response_text = "I apologize, but my AI is currently offline. I cannot process your request."
                                logger.warning(f"[{time.time()}] AI is offline, sending fallback response.")
                            
                            bot_response_text = ai_response_text # Set bot_response_text from AI

                        # --- Record and Send Bot Message ---
                        record_bot_message_start_time = time.time()
                        # Use bot_response_text, which is either from handover or AI
                        record_message(conversation_id, "bot", bot_response_text, response_to_message_id=recorded_user_message.id)
                        record_bot_message_end_time = time.time()
                        logger.info(f"[{time.time()}] record_message for bot took {(record_bot_message_end_time - record_bot_message_start_time)*1000:.2f} ms.")

                        send_whatsapp_start_time = time.time()
                        phone_number_id_for_sending = change['value']['metadata']['phone_number_id']
                        # Send bot_response_text
                        send_whatsapp_message(phone_number_id_for_sending, from_number, bot_response_text)
                        send_whatsapp_end_time = time.time()
                        logger.info(f"[{time.time()}] send_whatsapp_message took {(send_whatsapp_end_time - send_whatsapp_start_time)*1000:.2f} ms. Successfully sent AI/Handover response to {from_number}.")

                        return "Message processed", 200

                    else:
                        logger.info(f"[{time.time()}] Received unsupported message type: {message.get('type')}. Skipping processing for now.")

            elif 'statuses' in change['value']:
                logger.info(f"[{time.time()}] Received a WhatsApp message status update. Acknowledging.")
                return "Status update acknowledged", 200

    return "Message processed", 200
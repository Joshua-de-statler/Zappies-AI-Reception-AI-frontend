# app/utils/whatsapp_utils.py

import logging
import json
import requests
import os
import time
import mimetypes # New import for handling file types
from datetime import datetime, timedelta
from dotenv import load_dotenv # Ensure this import is at the top for load_dotenv()
from PIL import Image # New import for image handling
import io # New import for in-memory file handling

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
                                if 'type' in message and message['type'] in ['text', 'image', 'audio', 'button', 'reaction', 'interactive', 'video', 'document', 'sticker', 'location', 'contacts', 'order', 'system', 'unknown']:
                                    return message['type']
                        elif 'statuses' in change['value']:
                            return "status"
    return "unsupported"

def get_media_url(media_id: str):
    """
    Retrieves a temporary, authenticated URL for a media file from the WhatsApp Cloud API.
    The URL is valid for 5 minutes.
    """
    url = f"{GRAPH_API_URL}/{media_id}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("url")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching media URL for ID {media_id}: {e}", exc_info=True)
        return None

def download_media(media_url: str):
    """
    Downloads media content from a given URL using the access token.
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    try:
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading media from URL {media_url}: {e}", exc_info=True)
        return None

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
    
    # Process 'message' types
    for entry in data['entry']:
        for change in entry['changes']:
            if 'messages' in change['value']:
                for message in change['value']['messages']:
                    # Extract common message data
                    from_number = message['from'] # User's WhatsApp ID (phone number)
                    user_name = change['value']['contacts'][0]['profile']['name'] # User's name
                    meta_message_id = message['id'] # Meta's unique message ID for deduplication
                    phone_number_id_for_sending = change['value']['metadata']['phone_number_id']

                    logger.info(f"[{time.time()}] Received incoming message from {user_name} ({from_number}) of type '{message['type']}' (Meta ID: {meta_message_id})")

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

                    # --- Handle different message types ---
                    message_content = None # Initialize content to be passed to AI
                    ai_input_parts = []

                    if message['type'] == 'text':
                        message_body = message['text']['body']
                        message_content = message_body
                        ai_input_parts.append({"text": message_body})
                        
                        # Check for handover keywords only for text messages
                        user_message_lower = message_body.lower()
                        handover_triggered = False
                        bot_response_text = ""
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
                                    record_conversion_event(conversation_id, "meeting_scheduled_calendly", {"user_intent": message_body, "calendly_link_provided": CALENDLY_LINK})
                                logger.info(f"[{time.time()}] Handover triggered by keyword: '{keyword}'. Providing Calendly link.")
                                handover_triggered = True
                                break
                        
                        if handover_triggered:
                            # Record and send handover message
                            recorded_user_message, is_duplicate = record_message(conversation_id, "user", message_content, meta_message_id=meta_message_id)
                            if recorded_user_message is None or is_duplicate: return "Failed to record or duplicate", 200
                            record_message(conversation_id, "bot", bot_response_text, response_to_message_id=recorded_user_message.id)
                            send_whatsapp_message(phone_number_id_for_sending, from_number, bot_response_text)
                            return "Handover message processed", 200


                    elif message['type'] == 'image':
                        image_id = message['image']['id']
                        image_caption = message['image'].get('caption', '')
                        logger.info(f"[{time.time()}] Processing image with ID: {image_id} and caption: '{image_caption}'")
                        
                        media_url = get_media_url(image_id)
                        if not media_url:
                            send_whatsapp_message(phone_number_id_for_sending, from_number, "I'm sorry, I was unable to retrieve that image. Please try again.")
                            return "Error retrieving image", 500
                        
                        image_data = download_media(media_url)
                        if not image_data:
                            send_whatsapp_message(phone_number_id_for_sending, from_number, "I'm sorry, I was unable to download that image. Please try again.")
                            return "Error downloading image", 500
                        
                        image_mime_type = 'image/jpeg' # WhatsApp documentation often uses 'image/jpeg', you can add logic to get it from API response
                        
                        message_content = f"User sent an image with caption: '{image_caption}'"
                        ai_input_parts.append({"text": "The user sent an image. Please describe the image and answer any questions in the caption. Then, continue the conversation as the sales bot."})
                        ai_input_parts.append({"mime_type": image_mime_type, "data": image_data})
                        ai_input_parts.append({"text": image_caption})
                        logger.info(f"[{time.time()}] Successfully prepared image data for Gemini.")

                    elif message['type'] == 'audio':
                        audio_id = message['audio']['id']
                        audio_mime_type = message['audio']['mime_type']
                        logger.info(f"[{time.time()}] Processing audio with ID: {audio_id}")
                        
                        media_url = get_media_url(audio_id)
                        if not media_url:
                            send_whatsapp_message(phone_number_id_for_sending, from_number, "I'm sorry, I was unable to retrieve that audio note. Please try again.")
                            return "Error retrieving audio", 500
                        
                        audio_data = download_media(media_url)
                        if not audio_data:
                            send_whatsapp_message(phone_number_id_for_sending, from_number, "I'm sorry, I was unable to download that audio note. Please try again.")
                            return "Error downloading audio", 500

                        message_content = f"User sent an audio note (voice note)."
                        ai_input_parts.append({"text": "The user sent a voice note. Please transcribe the voice note and respond to the transcription as the Naturarose sales agent. Remember your goal is to book a consultation."})
                        ai_input_parts.append({"mime_type": audio_mime_type, "data": audio_data})
                        logger.info(f"[{time.time()}] Successfully prepared audio data for Gemini.")

                    else:
                        logger.info(f"[{time.time()}] Received unsupported message type: {message['type']}. Skipping processing for now.")
                        return "Unsupported message type", 200
                    
                    # --- If we get here, it's a message to be processed by AI (not a handover) ---
                    # Record the user message in the database, handling duplicates
                    recorded_user_message, is_duplicate = record_message(conversation_id, "user", message_content, meta_message_id=meta_message_id)

                    if recorded_user_message is None:
                        logger.error(f"[{time.time()}] Failed to record user message (Meta ID {meta_message_id}). Skipping processing.")
                        return "Failed to record message", 500

                    if is_duplicate:
                        logger.info(f"[{time.time()}] Meta Message ID {meta_message_id} was identified as a duplicate. Skipping further processing and responding with 200 OK.")
                        return "Message already processed", 200

                    # Now, call the GeminiService to get the AI response
                    bot_response_text = ""
                    if ai_enabled and ai_input_parts:
                        start_ai_time = time.time()
                        # Pass the prepared parts list to the Gemini service
                        ai_response_text = gemini_service.generate_response(ai_input_parts, conversation_id)
                        bot_response_text = ai_response_text
                        end_ai_time = time.time()
                        logger.info(f"[{time.time()}] Gemini response took {(end_ai_time - start_ai_time)*1000:.2f} ms.")
                    else:
                        bot_response_text = "I apologize, but my AI is currently offline. I cannot process your request."
                        logger.warning(f"[{time.time()}] AI is offline, sending fallback response.")

                    # --- Record and Send Bot Message ---
                    record_bot_message_start_time = time.time()
                    record_message(conversation_id, "bot", bot_response_text, response_to_message_id=recorded_user_message.id)
                    record_bot_message_end_time = time.time()
                    logger.info(f"[{time.time()}] record_message for bot took {(record_bot_message_end_time - record_bot_message_start_time)*1000:.2f} ms.")
                    
                    send_whatsapp_start_time = time.time()
                    send_whatsapp_message(phone_number_id_for_sending, from_number, bot_response_text)
                    send_whatsapp_end_time = time.time()
                    logger.info(f"[{time.time()}] send_whatsapp_message took {(send_whatsapp_end_time - send_whatsapp_start_time)*1000:.2f} ms. Successfully sent AI/Handover response to {from_number}.")

                    return "Message processed", 200

            elif 'statuses' in change['value']:
                logger.info(f"[{time.time()}] Received a WhatsApp message status update. Acknowledging.")
                return "Status update acknowledged", 200

    return "Message processed", 200
import os
import requests
import logging
import shelve
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Variables directly from your .env file
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
WHATSAPP_API_VERSION = os.getenv("VERSION", "v18.0") # Use your VERSION from .env, default to v18.0 if not found

if not PHONE_NUMBER_ID:
    logger.error("PHONE_NUMBER_ID not found in environment variables.")
    raise ValueError("PHONE_NUMBER_ID is not set.")
if not ACCESS_TOKEN:
    logger.error("ACCESS_TOKEN not found in environment variables.")
    raise ValueError("ACCESS_TOKEN is not set.")

# Import Gemini utility for AI response generation - NOW from gemini_service
from app.services.gemini_service import generate_response # Adjusted path

# --- Deduplication Logic ---
def has_message_been_processed(message_id):
    """
    Checks if a message ID has already been processed within a recent time window.
    This prevents duplicate responses due to webhook retries.
    """
    with shelve.open("processed_messages_db", writeback=True) as processed_shelf:
        # Clean up old entries (e.g., older than 5 minutes = 300 seconds)
        five_minutes_ago = time.time() - 300
        keys_to_delete = [key for key, timestamp in processed_shelf.items() if timestamp < five_minutes_ago]
        for key in keys_to_delete:
            del processed_shelf[key]
            logger.debug(f"Cleaned up old message ID: {key}")

        return message_id in processed_shelf

def mark_message_as_processed(message_id):
    """
    Marks a message ID as processed with a timestamp.
    """
    with shelve.open("processed_messages_db") as processed_shelf:
        processed_shelf[message_id] = time.time()
        logger.info(f"Marked message ID as processed: {message_id}")

# --- WhatsApp Message Sending ---
def send_whatsapp_message(to_wa_id, message_body):
    """
    Sends a text message to a WhatsApp user using Meta's Cloud API.
    """
    # Construct URL using your PHONE_NUMBER_ID and WHATSAPP_API_VERSION from .env
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        # Use your ACCESS_TOKEN from .env
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "text",
        "text": {"body": message_body},
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Message sent to {to_wa_id}: {message_body}")
        logger.debug(f"WhatsApp API response: {response.json()}")
        return True
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while sending WhatsApp message: {http_err} - {response.text}")
        return False
    except Exception as err:
        logger.error(f"Other error occurred while sending WhatsApp message: {err}")
        return False

# --- Main WhatsApp Message Processing Handler ---
def process_and_reply_to_whatsapp(webhook_data):
    """
    Parses the incoming Meta webhook data, handles deduplication,
    generates AI response, and sends the message back to WhatsApp.
    This function runs in a separate thread.
    """
    try:
        # This is a common structure for Meta WhatsApp webhooks.
        # You might need to adjust this based on your actual payload if it differs.
        entry = webhook_data['entry'][0]
        change = entry['changes'][0]
        value = change['value']
        
        # Check if it's a message event
        if 'messages' in value:
            for message_obj in value['messages']:
                message_type = message_obj.get('type')
                
                # We are primarily interested in text messages from users
                if message_type == 'text':
                    wa_id = message_obj['from'] # User's WhatsApp ID
                    message_body = message_obj['text']['body'] # The text content
                    message_id = message_obj['id'] # Unique message ID from Meta
                    
                    # You might need to retrieve the user's name from Meta's API or
                    # use a placeholder if not available in the webhook directly.
                    name = value.get('contacts', [{}])[0].get('profile', {}).get('name', 'WhatsApp User')

                    logger.info(f"Processing incoming message from {name} ({wa_id}): {message_body} (ID: {message_id})")

                    # --- Deduplication Check ---
                    if has_message_been_processed(message_id):
                        logger.warning(f"Message ID {message_id} already processed. Skipping.")
                        return # Stop processing this duplicate message

                    # Mark message as processed BEFORE generating response
                    mark_message_as_processed(message_id)

                    # --- Generate AI Response ---
                    ai_response_text = generate_response(message_body, wa_id, name)
                    
                    # --- Send Response Back to WhatsApp ---
                    if ai_response_text:
                        success = send_whatsapp_message(wa_id, ai_response_text)
                        if not success:
                            logger.error(f"Failed to send AI response to {wa_id}.")
                        else:
                            logger.info(f"Successfully sent AI response to {wa_id}.")
                    else:
                        logger.warning(f"No AI response generated for {wa_id}.")

                elif message_type == 'referral':
                    logger.info(f"Received referral message: {message_obj}")
                elif message_type == 'reaction':
                    logger.info(f"Received reaction message: {message_obj}")
                elif message_type == 'image' or message_type == 'video' or message_type == 'document':
                    logger.info(f"Received media message (type: {message_type}): {message_obj}")
                    send_whatsapp_message(message_obj['from'], "I can't currently process images or videos. Please tell me in text how I can help!")
                else:
                    logger.info(f"Received unhandled message type: {message_type} - {message_obj}")
                    send_whatsapp_message(message_obj['from'], "I received your message, but I'm currently set up to respond mainly to text messages. Could you please rephrase your query in text?")
        
        # Handle 'statuses' for message delivery notifications (optional)
        elif 'statuses' in value:
            status = value['statuses'][0]
            logger.info(f"Message status update for ID {status['id']}: {status['status']} - {status.get('errors')}")

    except IndexError:
        logger.error(f"Malformed webhook data received: {webhook_data}. Skipping processing.")
    except Exception as e:
        logger.error(f"Unhandled error in process_and_reply_to_whatsapp: {e}", exc_info=True)
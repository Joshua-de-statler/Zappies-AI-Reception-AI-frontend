# app/utils/whatsapp_utils.py

import logging
from flask import current_app, jsonify
import json
import requests
from datetime import datetime
import re

# Import the new database service
from app.services import database_service
# Import the Gemini service (if you uncommented it for AI)
from app.services.gemini_service import generate_response as gemini_generate_response


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


# Placeholder generate_response function (if AI is not yet active)
# If you enable Gemini AI, this function will be replaced by gemini_generate_response
def generate_response(message_body, wa_id, name):
    # This is the placeholder function that will be used if Gemini is not configured.
    # It simply converts the input text to uppercase.
    return message_body.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10 # You can increase this timeout for testing, e.g., 30
        )
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        log_http_response(response) # Log success response from WhatsApp API
        return jsonify({"status": "success", "message": "Message sent"}), 200
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Timeout occurred"}), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return jsonify({"status": "error", "message": f"Failed to send message: {str(e)}"}), 500


def process_text_for_whatsapp(text):
    # Remove content within double brackets (e.g., 【...】)
    pattern = r"【.*?】"
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message_timestamp = datetime.fromtimestamp(int(body["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"]))


    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # --- Database Integration: User message & Conversation setup (happens first) ---
    company = database_service.get_or_create_company()
    company_id = company.id

    whatsapp_user = database_service.get_or_create_whatsapp_user(wa_id, name, company_id)
    user_id = whatsapp_user.id

    conversation = database_service.get_or_create_conversation(user_id, company_id)
    conversation_id = conversation.id

    last_bot_message = database_service.Message.query.filter_by(
        conversation_id=conversation_id,
        sender_type='bot'
    ).order_by(database_service.Message.timestamp.desc()).first()

    user_message = database_service.record_message(
        conversation_id=conversation_id,
        sender_type='user',
        content=message_body
    )

    if last_bot_message:
        database_service.calculate_and_update_response_time(
            last_bot_message.id, user_message.timestamp, company_id
        )
    # --- End Database Integration: User message & Conversation setup ---


    # Conditional AI Integration:
    if current_app.config.get("GOOGLE_API_KEY"): # Check if Gemini API key is set
        response_text = gemini_generate_response(message_body, wa_id, name)
    else:
        response_text = generate_response(message_body, wa_id, name) # Placeholder function

    response_text = process_text_for_whatsapp(response_text)

    # --- NEW ORDER: Attempt to Send Message FIRST, THEN Record Bot Message ---
    data_to_send = get_text_message_input(wa_id, response_text)
    
    # Attempt to send the message to WhatsApp
    send_result = send_message(data_to_send) 

    # Check if send_message returned an error response (Flask jsonify returns tuple)
    if isinstance(send_result, tuple) and send_result[1] != 200:
        logging.error(f"Failed to send message to WhatsApp. Status: {send_result[1] if isinstance(send_result, tuple) else 'unknown'}. Bot's intended message will still be recorded.")
        # You could add more sophisticated error handling here (e.g., retry queue, status in DB)
    else:
        logging.info("Message successfully sent to WhatsApp API (initial response from API was OK).")

    # Record Bot Message in DB (after attempting to send)
    # This ensures we log the bot's response even if WhatsApp sending failed, for debugging.
    bot_message = database_service.record_message(
        conversation_id=conversation_id,
        sender_type='bot',
        content=response_text,
        response_to_message_id=user_message.id # Link bot's response to the user's message
    )
    # --- End NEW ORDER ---


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
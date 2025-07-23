# app/utils/whatsapp_utils.py
import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_message(recipient_id: str, message: str):
    """
    Sends a text message via the WhatsApp Business Cloud API.
    """
    # Changed to look for GRAPH_API_TOKEN as per your .env file's intended use
    GRAPH_API_TOKEN = os.getenv("GRAPH_API_TOKEN")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    GRAPH_API_URL = os.getenv("GRAPH_API_URL", "https://graph.facebook.com/v18.0")

    if not GRAPH_API_TOKEN:
        logger.error("GRAPH_API_TOKEN environment variable not set.")
        return False
    if not PHONE_NUMBER_ID:
        logger.error("PHONE_NUMBER_ID environment variable not set.")
        return False

    url = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message}
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        logger.info(f"Message sent successfully to {recipient_id}. Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to {recipient_id}: {e}")
        if response is not None:
            logger.error(f"WhatsApp API Error Response: {response.text}")
        return False
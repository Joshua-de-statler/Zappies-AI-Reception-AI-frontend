# app/views.py
import os
import json # Import json
from flask import Blueprint, request, jsonify # Import jsonify
import logging
import time # Import time for logging

from app.config import VERIFY_TOKEN
from app.utils.whatsapp_utils import process_whatsapp_message, send_whatsapp_message

webhook_blueprint = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

@webhook_blueprint.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                logger.info("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed: Invalid token or mode.")
                return 'Verification token mismatch', 403
        else:
            logger.warning("Webhook verification failed: Missing mode or token.")
            return 'Missing parameters', 400
    elif request.method == 'POST':
        data = request.get_json()
        # Log the full incoming data for debugging purposes (be cautious with sensitive data in production)
        logger.info(f"[{time.time()}] Webhook POST received. Data: {json.dumps(data, indent=2)}")
        try:
            status_message, status_code = process_whatsapp_message(data)
            logger.info(f"[{time.time()}] Webhook processing complete. Status: {status_message}, Code: {status_code}")
            # Ensure a JSON response is always returned, even for 200 OK
            return jsonify({"status": status_message}), status_code
        except Exception as e:
            logger.exception(f"[{time.time()}] Error during webhook processing: {e}")
            # Always return a JSON response for errors too
            return jsonify({"status": "error", "message": "Internal server error"}), 500
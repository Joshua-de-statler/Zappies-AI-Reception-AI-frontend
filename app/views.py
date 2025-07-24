# app/views.py

from flask import Blueprint, request, jsonify, current_app # Import current_app
import logging
import os
import json
import time # Import time for logging

# Import the necessary utility functions from whatsapp_utils
from app.utils.whatsapp_utils import (
    process_whatsapp_message
)

webhook_blueprint = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

# --- Webhook for WhatsApp incoming messages ---
@webhook_blueprint.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # Access VERIFY_TOKEN from current_app.config, not direct import
    VERIFY_TOKEN = current_app.config.get("VERIFY_TOKEN")

    if request.method == 'GET':
        # VERIFICATION request from Facebook/Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                logger.info("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed: Invalid token or mode.")
                return "Verification token mismatch", 403
        logger.warning("Webhook verification failed: Missing parameters.")
        return "Missing parameters", 400

    elif request.method == 'POST':
        # INCOMING MESSAGE or STATUS UPDATE from Facebook/Meta
        data = request.get_json()
        logger.info(f"[{time.time()}] Webhook POST received. Data: {json.dumps(data, indent=2)}")

        try:
            # Process the WhatsApp data (can be a message or a status update)
            status_message, status_code = process_whatsapp_message(data)
            logger.info(f"[{time.time()}] Webhook processing complete. Status: {status_message}, Code: {status_code}")
            return jsonify({"status": status_message}), status_code
        except Exception as e:
            logger.exception(f"[{time.time()}] Error during webhook processing: {e}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    return jsonify({"status": "Method not allowed"}), 405
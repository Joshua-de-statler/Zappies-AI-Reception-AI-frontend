# app/routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
from app.utils.whatsapp_utils import process_whatsapp_message, is_valid_whatsapp_message

# Define the Blueprint
whatsapp_blueprint = Blueprint("whatsapp", __name__)

@whatsapp_blueprint.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Handles the webhook verification request from Facebook.
    """
    logging.info("Verifying webhook")
    VERIFY_TOKEN = current_app.config["VERIFY_TOKEN"] # Access VERIFY_TOKEN from app config
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.info("VERIFICATION_FAILED: Token mismatch")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    logging.info("VERIFICATION_FAILED: Missing parameters")
    return jsonify({"status": "error", "message": "Missing parameters"}), 400


@whatsapp_blueprint.route("/webhook", methods=["POST"])
def webhook_post():
    """
    Handles incoming webhook events from WhatsApp.
    """
    body = request.get_json()
    logging.info(f"Received webhook event: {body}")

    # Check if it's a valid WhatsApp message event
    if is_valid_whatsapp_message(body):
        try:
            process_whatsapp_message(body)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # Not a WhatsApp message event (could be a status update, etc.)
        logging.info("Not a valid WhatsApp message event, ignoring.")
        return jsonify({"status": "ignored", "message": "Not a valid WhatsApp message event"}), 200
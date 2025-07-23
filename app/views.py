# app/views.py
from flask import Flask, request, jsonify
import logging
import os
import re # Import re for parsing the JSON
import json # Import json for parsing the JSON

# Import your services
from app.services.gemini_service import GeminiService
from app.utils.whatsapp_utils import send_whatsapp_message
from app.database import supabase_init # You might need this if you initialize supabase here
from app.services.supa_service import save_message_to_db, get_previous_messages # Import Supabase service functions
from app.services.meeting_service import parse_gemini_meeting_response, handle_meeting_request # Import new meeting service functions

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GeminiService (ensure it's done once per app lifecycle)
# It's better to instantiate this once globally if you want to maintain
# a single chat session for the bot's persona.
gemini_service = GeminiService()

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # WhatsApp webhook verification
        logger.info("Received GET request for webhook verification.")
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # Verify the token
        if mode and token:
            if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN"):
                logger.info("Webhook verified successfully!")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed: Invalid token or mode.")
                return jsonify({"status": "error", "message": "Verification failed"}), 403
        else:
            logger.warning("Webhook verification failed: Missing parameters.")
            return jsonify({"status": "error", "message": "Missing parameters"}), 400

    elif request.method == "POST":
        # Handle incoming messages from WhatsApp
        data = request.get_json()
        logger.info(f"Received POST request data: {json.dumps(data, indent=2)}")

        if not data or "entry" not in data:
            logger.warning("Invalid webhook data: Missing 'entry' field.")
            return jsonify({"status": "error", "message": "Invalid webhook data"}), 400

        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    for message in value["messages"]:
                        sender_id = message["from"]  # WhatsApp user ID
                        message_type = message["type"]

                        if message_type == "text":
                            user_message = message["text"]["body"]
                            logger.info(f"Received message from {sender_id}: {user_message}")

                            # Save incoming message to DB
                            save_message_to_db(sender_id, "user", user_message)

                            # --- Process message with Gemini and check for meeting intent ---
                            gemini_raw_response = gemini_service.generate_response(user_message)
                            logger.info(f"Gemini raw response: {gemini_raw_response}")

                            response_to_send = ""
                            meeting_details = parse_gemini_meeting_response(gemini_raw_response)

                            if meeting_details and meeting_details.get("intent") == "schedule_meeting":
                                # Gemini detected a meeting intent, use the meeting service
                                response_to_send = handle_meeting_request(meeting_details, sender_id)
                                # The natural language part of Gemini's response can be discarded here
                                # or you could try to combine it. For now, meeting_service will craft the full message.
                            else:
                                # No meeting intent, use Gemini's standard response
                                response_to_send = gemini_raw_response


                            # Send the determined response back to WhatsApp
                            send_whatsapp_message(sender_id, response_to_send)

                            # Save outgoing message to DB
                            save_message_to_db(sender_id, "bot", response_to_send)

                        else:
                            # Handle other message types (e.g., images, videos, audio)
                            response_message = "I can only process text messages at the moment. Please send a text."
                            logger.info(f"Received non-text message from {sender_id} (type: {message_type}). Responding: {response_message}")
                            send_whatsapp_message(sender_id, response_message)
                            save_message_to_db(sender_id, "bot", response_message)

        return jsonify({"status": "success"}), 200

    else:
        logger.warning(f"Received unsupported HTTP method: {request.method}")
        return jsonify({"status": "error", "message": "Method not allowed"}), 405

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
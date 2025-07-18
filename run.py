import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from threading import Thread

# Import your utility functions with correct paths
from app.services.gemini_service import generate_response # Adjusted path
from app.utils.whatsapp_utils import send_whatsapp_message, process_and_reply_to_whatsapp # Adjusted path

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Environment variable for Webhook verification - matches your .env 'VERIFY_TOKEN'
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    logger.error("VERIFY_TOKEN not found in environment variables. Please set it in your .env file.")
    raise ValueError("VERIFY_TOKEN is not set.")

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFICATION_SUCCESS")
            return challenge, 200
        else:
            logger.warning("WEBHOOK_VERIFICATION_FAILED: Token mismatch or invalid mode")
            return "Verification token mismatch", 403
    logger.warning("WEBHOOK_VERIFICATION_FAILED: Missing parameters")
    return "Missing parameters", 400

@app.route('/webhook', methods=['POST'])
def webhook_post():
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")

        response_data = {"status": "success", "message": "Webhook received and acknowledged."}
        Thread(target=process_and_reply_to_whatsapp, args=(data,)).start()
        
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error processing webhook POST request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
import hmac
import hashlib
from functools import wraps
import logging
from flask import request, abort, current_app

logger = logging.getLogger(__name__)

def signature_required(f):
    """
    Decorator to verify the X-Hub-Signature-256 header for incoming WhatsApp webhooks.
    This ensures that the request truly originates from Meta and has not been tampered with.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Retrieve the App Secret from Flask's current application configuration
        app_secret = current_app.config.get("APP_SECRET")
        if not app_secret:
            logger.error("APP_SECRET is not configured in Flask app. Cannot verify webhook signature.")
            abort(500) # Internal Server Error if secret is missing

        # Get the X-Hub-Signature-256 header from the request
        # This header contains the HMAC SHA256 signature from Meta
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header:
            logger.warning("X-Hub-Signature-256 header missing from webhook request.")
            abort(400) # Bad Request if signature is missing

        # Extract the hash value (e.g., "sha256=abcdef12345...")
        # We only need the part after "sha256="
        try:
            sha_name, signature = signature_header.split("=")
            if sha_name != "sha256":
                logger.warning(f"Unsupported X-Hub-Signature-256 algorithm: {sha_name}.")
                abort(400)
        except ValueError:
            logger.warning("Malformed X-Hub-Signature-256 header format.")
            abort(400)

        # Get the raw request body
        # It's crucial to use get_data() and not get_json() here,
        # as get_json() parses the JSON, which might alter the string
        # and result in an incorrect signature hash.
        request_body = request.get_data()

        # Compute the HMAC SHA256 signature using your App Secret and the request body
        computed_hash = hmac.new(
            app_secret.encode('utf-8'), # Key must be bytes
            request_body,
            hashlib.sha256
        ).hexdigest()

        # Compare the computed hash with the signature received in the header
        if not hmac.compare_digest(computed_hash, signature):
            logger.warning("Webhook signature mismatch. Request might be unauthorized or tampered with.")
            abort(403) # Forbidden if signatures do not match

        # If everything passes, proceed to the decorated function (your webhook_post logic)
        return f(*args, **kwargs)
    return decorated_function
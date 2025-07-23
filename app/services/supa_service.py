# app/services/supa_service.py
from supabase import create_client, Client
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client globally
try:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

    if not SUPABASE_URL:
        logger.error("SUPABASE_URL environment variable not set.")
        raise ValueError("SUPABASE_URL is missing.")
    if not SUPABASE_KEY:
        logger.error("SUPABASE_KEY environment variable not set.")
        raise ValueError("SUPABASE_KEY is missing.")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully.")

except Exception as e:
    logger.exception(f"Error initializing Supabase client: {e}")
    raise # Re-raise to prevent the worker from booting if Supabase connection fails

def save_message_to_db(sender_id: str, sender_type: str, message_content: str):
    """
    Saves a message to the 'messages' table in Supabase.
    The message content will be stored in the 'content' column.
    """
    try:
        # Table name is 'messages', column name is 'content'
        data, count = supabase.table('messages').insert({
            'sender_id': sender_id,
            'sender_type': sender_type,
            'content': message_content # Changed column name to 'content'
        }).execute()
        logger.info(f"Message saved to DB: {data}")
    except Exception as e:
        logger.error(f"Failed to save message to DB: {e}")

def get_previous_messages(sender_id: str, limit: int = 5):
    """
    Retrieves previous messages for a given sender_id from the 'messages' table.
    Orders by timestamp descending and limits the result.
    """
    try:
        # Table name is 'messages'
        response = supabase.table('messages').select("*").eq(
            'sender_id', sender_id
        ).order('timestamp', desc=True).limit(limit).execute()

        # The data is in response.data, and the relevant message content will be in the 'content' field
        messages = response.data
        logger.info(f"Retrieved {len(messages)} previous messages for {sender_id}.")
        return messages[::-1] # Return in chronological order
    except Exception as e:
        logger.error(f"Failed to retrieve previous messages from DB: {e}")
        return []
import google.generativeai as genai
import shelve
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
# Ensure you have GOOGLE_API_KEY set in your .env file
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    logging.error("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
    raise ValueError("GOOGLE_API_KEY is not set.")

genai.configure(api_key=GEMINI_API_KEY)

# Use context manager to ensure the shelf file is closed properly
def check_if_thread_exists(wa_id):
    """
    Checks if a conversation thread exists for a given WhatsApp ID.
    Returns the thread ID if it exists, otherwise None.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    """
    Stores a new conversation thread ID for a given WhatsApp ID.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        threads_shelf[wa_id] = thread_id
        logging.info(f"Stored new thread for WA_ID: {wa_id}, Thread ID: {thread_id}")

def delete_thread(wa_id):
    """
    Deletes a conversation thread for a given WhatsApp ID.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        if wa_id in threads_shelf:
            del threads_shelf[wa_id]
            logging.info(f"Deleted thread for WA_ID: {wa_id}")

def generate_response(message_body, wa_id, name):
    """
    Generates a response using the Gemini API, maintaining conversation history.
    """
    try:
        # Check if there is already a thread_id for the wa_id
        thread_id = check_if_thread_exists(wa_id)

        # Initialize the model using a supported name from your list
        # We're choosing 'gemini-1.5-flash-latest' for its balance of speed and capability
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        if thread_id is None:
            logging.info(f"Creating new Gemini chat session for {name} with wa_id {wa_id}")
            chat = model.start_chat(history=[])
            store_thread(wa_id, wa_id) # Store wa_id as its own "thread_id" placeholder
            logging.info(f"Started new chat session for {wa_id}")
        else:
            logging.info(f"Continuing Gemini chat session for {name} with wa_id {wa_id}")
            # As noted previously, for true conversational memory, you would load the history here:
            # e.g., chat = model.start_chat(history=load_history_for_user(wa_id))
            chat = model.start_chat(history=[]) # Starting with empty history for simplicity

        # Send the user's message to the Gemini model
        logging.info(f"Sending message to Gemini for {name} ({wa_id}): {message_body}")
        
        response = chat.send_message(message_body)
        
        # Extract the text from the response
        generated_message = response.text
        logging.info(f"Generated message from Gemini: {generated_message}")

        return generated_message

    except Exception as e:
        logging.error(f"Error communicating with Gemini API: {e}")
        # Optionally, delete the thread on error to allow a fresh start next time
        # delete_thread(wa_id) # Uncomment if you want to reset session on error
        return "Sorry, I'm having trouble connecting to the AI at the moment. Please try again later."
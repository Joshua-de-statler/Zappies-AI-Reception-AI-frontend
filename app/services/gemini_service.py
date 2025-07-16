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

        # If a thread doesn't exist, create one and store it
        if thread_id is None:
            logging.info(f"Creating new Gemini chat session for {name} with wa_id {wa_id}")
            # For Gemini, a "thread" is more conceptual within your application.
            # We'll just create a new model instance for a fresh chat session.
            # We use the wa_id as the 'thread_id' in our local shelve for simplicity
            # since Gemini's API doesn't have explicit 'thread' objects like OpenAI's Assistants.
            # Instead, we send the entire conversation history with each turn for context.
            # For simplicity here, we're starting a new chat if no 'thread_id' (wa_id in this case) is found.
            # For a true continuous conversation, you'd load past messages from a persistent storage.
            # For now, we'll store the wa_id itself to indicate an active session.
            store_thread(wa_id, wa_id) # Store wa_id as its own "thread_id" placeholder
            
            # Initialize a new chat session for this user
            model = genai.GenerativeModel('gemini-pro')
            chat = model.start_chat(history=[])
            logging.info(f"Started new chat session for {wa_id}")

        else:
            logging.info(f"Continuing Gemini chat session for {name} with wa_id {wa_id}")
            # In a real-world scenario, you would load the conversation history for this wa_id
            # from your persistent storage (e.g., a database) and pass it to model.start_chat(history=...).
            # For this example, we'll start a fresh chat on each call if the 'thread_id' mechanism is purely
            # for session tracking rather than full history retrieval.
            # To simulate memory, we will include the previous user message.
            model = genai.GenerativeModel('gemini-pro')
            chat = model.start_chat(history=[]) # Initialize chat with empty history for this simplified example

        # Send the user's message to the Gemini model
        logging.info(f"Sending message to Gemini for {name} ({wa_id}): {message_body}")
        
        # This sends the message and gets the response
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
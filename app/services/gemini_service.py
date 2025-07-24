# app/services/gemini_service.py

import os
import google.generativeai as genai
import logging
# Ensure this import is present for fetching history
from app.services.database_service import get_conversation_history_for_gemini

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        """
        Initializes the GeminiService by configuring the Google Generative AI client.
        Fetches the API key from environment variables.
        """
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                # Log an error and raise if the API key is missing
                logger.error("GOOGLE_API_KEY environment variable not set. Gemini service will not function.")
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            
            genai.configure(api_key=google_api_key)
            # Initialize the generative model
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("GeminiService initialized successfully with 'gemini-2.5-flash' model.")
        except Exception as e:
            # Catch any exceptions during initialization (e.g., network issues, invalid key)
            logger.error(f"Failed to initialize Gemini Pro model: {e}")
            self.model = None # Set model to None to indicate failure

    def generate_response(self, user_message: str, conversation_id: int = None) -> str:
        """
        Generates a response from the Gemini model.
        It can incorporate conversation history if a conversation_id is provided.

        Args:
            user_message (str): The current message from the user.
            conversation_id (int, optional): The ID of the current conversation.
                                             If provided, previous messages from this conversation
                                             will be fetched from the database and included as context.

        Returns:
            str: The generated response text from the Gemini model.
                 Returns a fallback message if the model is not available or an error occurs.
        """
        if not self.model:
            logger.warning("Attempted to generate response but Gemini model is not initialized.")
            return "I apologize, the AI model is currently unavailable."

        try:
            # Build the conversation context for Gemini
            contents = []
            if conversation_id:
                # Fetch past messages from the database for the given conversation
                history_from_db = get_conversation_history_for_gemini(conversation_id)
                if history_from_db:
                    contents.extend(history_from_db)
                    logger.debug(f"Fetched {len(history_from_db)} previous messages for context.")
                else:
                    logger.debug(f"No previous messages found for conversation ID {conversation_id}.")

            # Add the current user's message to the conversation history
            contents.append({"role": "user", "parts": [{"text": user_message}]})
            
            logger.info(f"Sending message to Gemini. Context length: {len(contents)} turns.")
            
            # Generate content using the model
            response = self.model.generate_content(contents)
            
            # Return the generated text
            return response.text
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}", exc_info=True)
            return "I'm sorry, I couldn't generate a response at this moment. Please try again."
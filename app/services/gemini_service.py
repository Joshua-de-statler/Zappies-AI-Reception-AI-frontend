# app/services/gemini_service.py

import os
import google.generativeai as genai
import logging
from app.services.database_service import get_conversation_history_for_gemini
from flask import current_app
from app.persona import PRIMER_MESSAGES # Import the persona

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        """
        Initializes the GeminiService by configuring the Google Generative AI client.
        """
        try:
            google_api_key = current_app.config.get("GOOGLE_API_KEY")
            if not google_api_key:
                logger.error("GOOGLE_API_KEY not set. Gemini service will not function.")
                raise ValueError("GOOGLE_API_KEY is not configured.")
            
            genai.configure(api_key=google_api_key)
            
            model_name = current_app.config.get("GEMINI_MODEL", "gemini-1.5-flash")
            self.model = genai.GenerativeModel(model_name)
            self.primer_messages = PRIMER_MESSAGES
            logger.info(f"GeminiService initialized with '{model_name}' and persona.")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
            self.model = None

    def generate_response(self, user_parts: list, conversation_id: int = None) -> str:
        """
        Generates a response from the Gemini model using conversation history and a predefined persona.
        """
        if not self.model:
            logger.warning("Attempted to generate response but Gemini model is not initialized.")
            return "I apologize, but my AI capabilities are currently offline. Please try again later."

        try:
            contents = []
            # Prepend the persona/primer messages
            contents.extend(self.primer_messages)

            # Add conversation history from the database
            if conversation_id:
                history_from_db = get_conversation_history_for_gemini(conversation_id)
                if history_from_db:
                    contents.extend(history_from_db)
                    logger.debug(f"Fetched {len(history_from_db)} previous messages for context.")

            # Add the current user's message
            contents.append({"role": "user", "parts": user_parts})

            logger.info(f"Sending request to Gemini with {len(contents)} parts.")

            # Generate the response
            response = self.model.generate_content(contents)
            
            return response.text
        
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}", exc_info=True)
            return "I'm sorry, I encountered a problem while processing your request. Please try again."
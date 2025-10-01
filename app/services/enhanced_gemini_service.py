# app/services/enhanced_gemini_service.py
import google.generativeai as genai
import logging
from typing import Dict, Any, Optional
from app.persona import PRIMER_MESSAGES
from flask import current_app
import json

logger = logging.getLogger(__name__)

class EnhancedGeminiService:
    """Enhanced Gemini service with context management and conversation flow"""
    
    def __init__(self):
        try:
            google_api_key = current_app.config.get("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY is not configured")
            
            genai.configure(api_key=google_api_key)
            
            # Initialize model with enhanced configuration
            generation_config = genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
            )
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
            
            model_name = current_app.config.get("GEMINI_MODEL", "gemini-1.5-flash")
            self.model = genai.GenerativeModel(
                model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            self.primer_messages = PRIMER_MESSAGES
            logger.info(f"Enhanced Gemini Service initialized with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Gemini Service: {e}")
            self.model = None
    
    def generate_contextual_response(
        self, 
        user_message: str, 
        context: Dict[str, Any],
        conversation_id: Optional[int] = None
    ) -> str:
        """Generate response with rich context"""
        
        if not self.model:
            return "I apologize, but I'm having technical difficulties. Please try again later."
        
        try:
            # Build enhanced context
            contents = []
            contents.extend(self.primer_messages)
            
            # Add conversation context
            if conversation_id:
                from app.services.database_service import get_conversation_history_for_gemini
                history = get_conversation_history_for_gemini(conversation_id)
                contents.extend(history)
            
            # Add current context as system message
            context_str = self._build_context_string(context)
            if context_str:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"[CONTEXT: {context_str}]"}]
                })
            
            # Add user message
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })
            
            # Generate response
            response = self.model.generate_content(contents)
            
            # Post-process response
            processed_response = self._post_process_response(response.text, context)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return "I encountered an issue processing your request. Please try again."
    
    def _build_context_string(self, context: Dict[str, Any]) -> str:
        """Build context string for the AI"""
        context_parts = []
        
        if 'user_name' in context:
            context_parts.append(f"User: {context['user_name']}")
        
        if 'company' in context:
            context_parts.append(f"Company: {context['company']}")
        
        if 'time_of_day' in context:
            context_parts.append(f"Time: {context['time_of_day']}")
        
        if 'platform' in context:
            context_parts.append(f"Platform: {context['platform']}")
        
        return " | ".join(context_parts)
    
    def _post_process_response(self, response: str, context: Dict[str, Any]) -> str:
        """Post-process AI response for personalization"""
        
        # Replace placeholders with actual values
        if 'user_name' in context:
            response = response.replace("[USER_NAME]", context['user_name'])
        
        if 'company' in context:
            response = response.replace("[COMPANY]", context['company'])
        
        # Ensure Calendly link is included when appropriate
        if any(keyword in response.lower() for keyword in ['schedule', 'demo', 'meeting', 'call']):
            calendly_link = current_app.config.get("CALENDLY_LINK")
            if calendly_link and calendly_link not in response:
                response += f"\n\nYou can schedule directly here: {calendly_link}"
        
        return response
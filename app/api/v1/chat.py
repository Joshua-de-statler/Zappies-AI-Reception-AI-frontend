# app/api/v1/chat.py
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.enhanced_gemini_service import EnhancedGeminiService
from app.services.database_service import (
    get_or_create_conversation,
    record_message,
    get_conversation_history_for_gemini
)
from app.models import User, Message
import logging

logger = logging.getLogger(__name__)

class ChatResource(Resource):
    decorators = [jwt_required()]
    
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('message', type=str, required=True)
        self.parser.add_argument('conversation_id', type=int)
        self.parser.add_argument('context', type=dict)
        self.gemini_service = EnhancedGeminiService()
        
    def post(self):
        user_id = get_jwt_identity()
        data = self.parser.parse_args()
        
        try:
            # Get or create conversation
            user = User.query.get(user_id)
            conversation = get_or_create_conversation(user.wa_id, user.company_id)
            
            # Record user message
            user_message, _ = record_message(
                conversation.id, 
                'user', 
                data['message']
            )
            
            # Generate AI response with context
            context = data.get('context', {})
            context.update({
                'user_name': user.name,
                'company': user.company_name,
                'conversation_history': get_conversation_history_for_gemini(conversation.id)
            })
            
            ai_response = self.gemini_service.generate_contextual_response(
                data['message'],
                context,
                conversation.id
            )
            
            # Record bot message
            bot_message, _ = record_message(
                conversation.id,
                'bot',
                ai_response,
                response_to_message_id=user_message.id
            )
            
            return {
                'message_id': bot_message.id,
                'response': ai_response,
                'conversation_id': conversation.id,
                'timestamp': bot_message.timestamp.isoformat()
            }, 200
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {'message': 'Failed to process message'}, 500
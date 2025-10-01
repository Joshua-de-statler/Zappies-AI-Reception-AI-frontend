# app/api/v1/chat.py
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.enhanced_gemini_service import EnhancedGeminiService
from app.services.database_service import (
    get_or_create_conversation,
    record_message
)
from app.models import User
from app.websocket.socketio_server import socketio  # Import your socketio instance
import logging

logger = logging.getLogger(__name__)

class ChatResource(Resource):
    decorators = [jwt_required()]

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('message', type=str, required=True, help='Message content is required')
        self.parser.add_argument('conversation_id', type=int)
        self.gemini_service = EnhancedGeminiService()

    def post(self):
        user_id = get_jwt_identity()
        data = self.parser.parse_args()

        try:
            user = User.query.get(user_id)
            if not user:
                return {'message': 'User not found'}, 404

            conversation = get_or_create_conversation(user.id, user.company_id)

            # Record the user's message in the database
            user_message, is_duplicate = record_message(
                conversation.id,
                'user',
                data['message']
            )

            if is_duplicate:
                return {'status': 'Message already processed'}, 200

            # Acknowledge the message and process the AI response in the background
            socketio.start_background_task(
                self.process_and_respond,
                user_id=user_id,
                user_name=user.name,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                user_text=data['message']
            )

            # Return an immediate success response to the client
            return {
                'message_id': user_message.id,
                'status': 'Message received and is being processed.'
            }, 202  # 202 Accepted means the request was accepted and will be processed

        except Exception as e:
            logger.error(f"Chat error for user {user_id}: {e}", exc_info=True)
            return {'message': 'Failed to process message'}, 500

    def process_and_respond(self, user_id, user_name, conversation_id, user_message_id, user_text):
        """
        This function runs in a background thread.
        It generates the AI response and emits it over the WebSocket.
        """
        try:
            context = {'user_name': user_name}
            ai_response = self.gemini_service.generate_contextual_response(
                user_text,
                context,
                conversation_id
            )

            bot_message, _ = record_message(
                conversation_id,
                'bot',
                ai_response,
                response_to_message_id=user_message_id
            )

            # Emit the final response to the specific user's room
            socketio.emit('new_message', {
                'message_id': bot_message.id,
                'content': ai_response,
                'sender_type': 'bot',
                'timestamp': bot_message.timestamp.isoformat(),
                'response_to': user_message_id
            }, room=f'user_{user_id}')

        except Exception as e:
            logger.error(f"Background AI processing failed for user {user_id}: {e}", exc_info=True)
            # Notify the client of the error via WebSocket
            socketio.emit('error', {
                'message': 'Failed to generate AI response.'
            }, room=f'user_{user_id}')
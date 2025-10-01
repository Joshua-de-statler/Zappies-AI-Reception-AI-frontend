# app/api/routes.py
from flask import Blueprint, request, jsonify
from app.services.database_service import get_or_create_conversation, record_message
from app.services.gemini_service import GeminiService

# This blueprint will be registered in your app/__init__.py
api_blueprint = Blueprint('api', __name__, url_prefix='/api/v1')

gemini_service = GeminiService()

@api_blueprint.route('/messages', methods=['POST'])
# In a real app, you'd add a @jwt_required decorator here
def handle_app_message():
    data = request.get_json()
    if not data or 'message' not in data or 'user_id' not in data:
        return jsonify({"error": "Missing message or user_id"}), 400

    user_id = data['user_id']
    user_message_content = data['message']
    
    # Assuming a default company for the free app
    # In a multi-tenant app, this would be dynamic
    company_id = 1 

    # 1. Get the conversation
    conversation = get_or_create_conversation(user_id, company_id)
    if not conversation:
        return jsonify({"error": "Could not establish conversation"}), 500

    # 2. Record the user's message
    user_message, _ = record_message(
        conversation_id=conversation.id,
        sender_type='user',
        content=user_message_content
    )

    # 3. Get a response from the AI
    ai_input_parts = [{"text": user_message_content}]
    bot_response_text = gemini_service.generate_response(ai_input_parts, conversation.id)

    # 4. Record the bot's response
    record_message(
        conversation_id=conversation.id,
        sender_type='bot',
        content=bot_response_text,
        response_to_message_id=user_message.id
    )
    
    # 5. Return the bot's response to the mobile app
    return jsonify({"reply": bot_response_text})
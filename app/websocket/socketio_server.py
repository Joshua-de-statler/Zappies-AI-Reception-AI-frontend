# app/websocket/socketio_server.py
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from flask import request
import logging
from app.services.database_service import get_or_create_conversation, record_message
from app.services.enhanced_gemini_service import EnhancedGeminiService
from app.models import User, Conversation
import json
from datetime import datetime

logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

# Track connected users
connected_users = {}

@socketio.on('connect')
def handle_connect(auth):
    """Handle WebSocket connection with JWT authentication"""
    try:
        # Verify JWT token
        token = auth.get('token') if auth else None
        if not token:
            logger.warning("Connection attempt without token")
            disconnect()
            return False
        
        # Verify token and get user identity
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        # Store connection info
        connected_users[request.sid] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow()
        }
        
        # Join user's personal room
        join_room(f'user_{user_id}')
        
        # Send connection confirmation
        emit('connection_established', {
            'status': 'connected',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"User {user_id} connected via WebSocket (sid: {request.sid})")
        return True
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        disconnect()
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    if request.sid in connected_users:
        user_id = connected_users[request.sid]['user_id']
        leave_room(f'user_{user_id}')
        del connected_users[request.sid]
        logger.info(f"User {user_id} disconnected (sid: {request.sid})")

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming message from client"""
    try:
        if request.sid not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[request.sid]['user_id']
        message_content = data.get('message')
        conversation_id = data.get('conversation_id')
        
        # Get user and conversation
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
        
        # Get or create conversation
        if not conversation_id:
            conversation = get_or_create_conversation(user.wa_id, user.company_id)
            conversation_id = conversation.id
        
        # Record user message
        user_msg, is_duplicate = record_message(
            conversation_id,
            'user',
            message_content,
            meta_message_id=data.get('client_message_id')
        )
        
        if is_duplicate:
            emit('message_status', {
                'status': 'duplicate',
                'message_id': user_msg.id
            })
            return
        
        # Emit message received confirmation
        emit('message_received', {
            'message_id': user_msg.id,
            'timestamp': user_msg.timestamp.isoformat(),
            'status': 'received'
        })
        
        # Broadcast to user's other devices
        emit('new_message', {
            'message_id': user_msg.id,
            'content': message_content,
            'sender_type': 'user',
            'timestamp': user_msg.timestamp.isoformat()
        }, room=f'user_{user_id}', skip_sid=request.sid)
        
        # Show typing indicator
        emit('typing_status', {'is_typing': True})
        
        # Generate AI response
        gemini_service = EnhancedGeminiService()
        ai_response = gemini_service.generate_contextual_response(
            message_content,
            {'user_name': user.name, 'company': user.company_name},
            conversation_id
        )
        
        # Record bot message
        bot_msg, _ = record_message(
            conversation_id,
            'bot',
            ai_response,
            response_to_message_id=user_msg.id
        )
        
        # Send AI response to all user's devices
        emit('typing_status', {'is_typing': False})
        emit('new_message', {
            'message_id': bot_msg.id,
            'content': ai_response,
            'sender_type': 'bot',
            'timestamp': bot_msg.timestamp.isoformat(),
            'response_to': user_msg.id
        }, room=f'user_{user_id}')
        
        # Check for conversion events
        check_and_emit_conversion_events(conversation_id, message_content, ai_response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        emit('error', {'message': 'Failed to process message'})

@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read"""
    try:
        if request.sid not in connected_users:
            return
        
        user_id = connected_users[request.sid]['user_id']
        message_ids = data.get('message_ids', [])
        
        # Update read status in database
        from app.models import Message
        Message.query.filter(
            Message.id.in_(message_ids)
        ).update({'is_read': True}, synchronize_session=False)
        db.session.commit()
        
        # Broadcast read status to other devices
        emit('messages_read', {
            'message_ids': message_ids
        }, room=f'user_{user_id}', skip_sid=request.sid)
        
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")

@socketio.on('typing_indicator')
def handle_typing(data):
    """Handle typing indicator"""
    if request.sid not in connected_users:
        return
    
    user_id = connected_users[request.sid]['user_id']
    is_typing = data.get('is_typing', False)
    
    # Broadcast to other participants (in a real chat app)
    emit('user_typing', {
        'user_id': user_id,
        'is_typing': is_typing
    }, room=f'user_{user_id}', skip_sid=request.sid)

def check_and_emit_conversion_events(conversation_id, user_message, bot_response):
    """Check for conversion events and emit them"""
    from app.services.database_service import record_conversion_event
    
    # Keywords that indicate conversion events
    conversion_keywords = {
        'demo': ['schedule demo', 'book demo', 'want demo'],
        'pricing': ['pricing', 'cost', 'how much'],
        'contact': ['contact sales', 'talk to someone', 'call me'],
        'interest': ['interested', 'sign up', 'get started']
    }
    
    user_msg_lower = user_message.lower()
    
    for event_type, keywords in conversion_keywords.items():
        if any(keyword in user_msg_lower for keyword in keywords):
            record_conversion_event(
                conversation_id,
                f'{event_type}_intent',
                {'user_message': user_message, 'bot_response': bot_response}
            )
            
            # Emit conversion event
            socketio.emit('conversion_event', {
                'type': event_type,
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room='analytics')  # Send to analytics dashboard
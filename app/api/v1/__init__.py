# app/api/v1/__init__.py
from flask import Blueprint
from flask_restful import Api
from flask_jwt_extended import JWTManager

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
api = Api(api_bp)

# Import and register resources
from app.api.v1.auth import AuthRegister, AuthLogin, AuthRefresh, AuthLogout
from app.api.v1.chat import ChatResource, ConversationResource, MessageHistoryResource
from app.api.v1.user import UserProfileResource, UserSettingsResource
from app.api.v1.analytics import AnalyticsResource, ConversionMetricsResource

# Authentication endpoints
api.add_resource(AuthRegister, '/auth/register')
api.add_resource(AuthLogin, '/auth/login')
api.add_resource(AuthRefresh, '/auth/refresh')
api.add_resource(AuthLogout, '/auth/logout')

# Chat endpoints
api.add_resource(ChatResource, '/chat/send')
api.add_resource(ConversationResource, '/conversations')
api.add_resource(MessageHistoryResource, '/conversations/<int:conversation_id>/messages')

# User management
api.add_resource(UserProfileResource, '/user/profile')
api.add_resource(UserSettingsResource, '/user/settings')

# Analytics
api.add_resource(AnalyticsResource, '/analytics/dashboard')
api.add_resource(ConversionMetricsResource, '/analytics/conversions')

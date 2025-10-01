# app/api/v1/__init__.py
from flask import Blueprint
from flask_restful import Api

api_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api = Api(api_bp)

# Import and register resources
from .auth import AuthRegister, AuthLogin, AuthRefresh, AuthLogout
from .chat import ChatResource
from .demos import DemoResource  # <-- IMPORT THE NEW DEMO RESOURCE

# Authentication endpoints
api.add_resource(AuthRegister, '/auth/register')
api.add_resource(AuthLogin, '/auth/login')
api.add_resource(AuthRefresh, '/auth/refresh')
api.add_resource(AuthLogout, '/auth/logout')

# Chat endpoint
api.add_resource(ChatResource, '/chat/send')

# Demo endpoint
api.add_resource(DemoResource, '/demos/initiate') # <-- REGISTER THE NEW ENDPOINT
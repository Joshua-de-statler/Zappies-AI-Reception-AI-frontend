# app/api/v1/auth.py
from flask_restful import Resource, reqparse
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User, RevokedToken
from app.utils.validators import validate_email, validate_phone
import logging

logger = logging.getLogger(__name__)

class AuthRegister(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email', type=str, required=True,
                                help='Email is required')
        self.parser.add_argument('password', type=str, required=True,
                                help='Password is required')
        self.parser.add_argument('phone', type=str, required=True,
                                help='Phone number is required')
        self.parser.add_argument('name', type=str, required=True,
                                help='Name is required')
        self.parser.add_argument('company_name', type=str)
        self.parser.add_argument('referral_code', type=str)

    def post(self):
        data = self.parser.parse_args()

        if not validate_email(data['email']):
            return {'message': 'Invalid email format'}, 400

        if not validate_phone(data['phone']):
            return {'message': 'Invalid phone number format'}, 400

        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered'}, 409

        if User.query.filter_by(phone=data['phone']).first():
            return {'message': 'Phone number already registered'}, 409

        try:
            user = User(
                email=data['email'],
                password_hash=generate_password_hash(data['password']),
                phone=data['phone'],
                name=data['name'],
                company_name=data.get('company_name'),
                referral_code=data.get('referral_code'),
                is_verified=False
            )

            db.session.add(user)
            db.session.commit()

            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            logger.info(f"New user registered: {user.email}")

            return {
                'message': 'User created successfully',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'phone': user.phone,
                    'is_verified': user.is_verified
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return {'message': 'Registration failed'}, 500

class AuthLogin(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email', type=str)
        self.parser.add_argument('phone', type=str)
        self.parser.add_argument('password', type=str, required=True)

    def post(self):
        data = self.parser.parse_args()

        if not data.get('email') and not data.get('phone'):
            return {'message': 'Email or phone number required'}, 400

        user = None
        if data.get('email'):
            user = User.query.filter_by(email=data['email']).first()
        elif data.get('phone'):
            user = User.query.filter_by(phone=data['phone']).first()

        if not user or not check_password_hash(user.password_hash, data['password']):
            return {'message': 'Invalid credentials'}, 401

        access_token = create_access_token(identity=user.id, fresh=True)
        refresh_token = create_refresh_token(identity=user.id)

        user.last_login = db.func.now()
        db.session.commit()

        return {
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_verified': user.is_verified
            }
        }, 200

class AuthRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """
        Generates a new access token from a valid refresh token.
        """
        current_user_id = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user_id, fresh=False)
        return {'access_token': new_access_token}, 200

class AuthLogout(Resource):
    @jwt_required()
    def post(self):
        """
        Revokes the current user's token by adding its JTI to a blacklist.
        """
        jti = get_jwt()['jti']
        try:
            revoked_token = RevokedToken(jti=jti)
            db.session.add(revoked_token)
            db.session.commit()
            return {'message': 'Access token has been revoked successfully.'}, 200
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return {'message': 'An error occurred while logging out.'}, 500
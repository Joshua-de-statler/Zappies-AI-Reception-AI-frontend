# app/api/v1/demos.py
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, db
import logging

logger = logging.getLogger(__name__)

# MOCK FUNCTIONS: In a real application, these would integrate with a
# telephony service like Twilio to make actual calls or send SMS.
def make_outbound_ai_call(phone_number: str):
    logger.info(f"DEMO TRIGGERED: Initiating a live AI call to {phone_number}")
    # your_telephony_service.calls.create(to=phone_number, from_='your_service_number', ...)
    pass

def send_outbound_ai_sms(phone_number: str):
    logger.info(f"DEMO TRIGGERED: Sending a live AI SMS to {phone_number}")
    # your_telephony_service.messages.create(to=phone_number, from_='your_service_number', ...)
    pass

class DemoResource(Resource):
    decorators = [jwt_required()]

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('type', type=str, required=True, choices=('call', 'sms'),
                                help="Type of demo must be 'call' or 'sms'")

    def post(self):
        user_id = get_jwt_identity()
        data = self.parser.parse_args()
        demo_type = data['type']

        try:
            user = User.query.get(user_id)
            if not user or not user.phone:
                return {'message': 'User or user phone number not found'}, 404

            if demo_type == 'call':
                make_outbound_ai_call(user.phone)
            elif demo_type == 'sms':
                send_outbound_ai_sms(user.phone)

            logger.info(f"'{demo_type}' demo successfully initiated for user {user_id} to {user.phone}")

            return {'status': f'{demo_type.capitalize()} demo has been initiated.'}, 200

        except Exception as e:
            logger.error(f"Error initiating demo for user {user_id}: {e}", exc_info=True)
            return {'message': 'Failed to start the demo'}, 500
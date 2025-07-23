# app/services/meeting_service.py
import logging
import json
import re # Import regex module for JSON extraction

logger = logging.getLogger(__name__)

# This is a placeholder for your actual Calendly or booking page URL
# You would replace this with your team's real booking link.
SALES_CALENDLY_LINK = "https://calendly.com/jeandre-c127/30min" # REPLACE THIS

def parse_gemini_meeting_response(gemini_response: str):
    """
    Parses the Gemini response to extract the JSON meeting intent, if present.
    """
    # Use regex to find the JSON block encapsulated by triple backticks
    match = re.search(r'```json\n({.*?})\n```', gemini_response, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            meeting_details = json.loads(json_str)
            logger.info(f"Successfully parsed meeting details from Gemini: {meeting_details}")
            return meeting_details
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Gemini response: {e}, JSON string: {json_str}")
            return None
    return None

def handle_meeting_request(parsed_meeting_details: dict, sender_id: str) -> str:
    """
    Constructs a WhatsApp response for a meeting scheduling request.
    In a real application, you might also:
    - Save the request to a database (e.g., leads table in Supabase).
    - Trigger an internal notification to the sales team (e.g., email, Slack).
    """
    if not parsed_meeting_details or parsed_meeting_details.get("intent") != "schedule_meeting":
        logger.warning(f"Meeting request handler called without valid meeting intent: {parsed_meeting_details}")
        return "I'm sorry, I couldn't understand the meeting details. Could you please specify your request again?"

    # Extract details from Gemini's parsed output
    topic = parsed_meeting_details.get("meeting_topic", "N/A").replace("N/A", "a discussion with our sales team")
    preferred_date = parsed_meeting_details.get("preferred_date", "N/A")
    preferred_time = parsed_meeting_details.get("preferred_time", "N/A")
    duration = parsed_meeting_details.get("duration", "N/A")

    # Construct a confirmation message
    confirmation_message = (
        "Excellent! I can definitely help you with that. "
        f"You're looking to schedule {topic}. "
    )

    if preferred_date != "N/A" and preferred_time != "N/A":
        confirmation_message += f"I see you're interested in {preferred_date} around {preferred_time}. "
    elif preferred_date != "N/A":
        confirmation_message += f"I've noted your preference for {preferred_date}. "
    elif preferred_time != "N/A":
        confirmation_message += f"I've noted your preference for around {preferred_time}. "

    confirmation_message += (
        "To make sure you connect with the right expert and find a time that fits perfectly, "
        "please use our secure booking page. You'll see real-time availability there:\n\n"
        f"👉 {SALES_CALENDLY_LINK}\n\n"
        "A sales representative will then reach out to confirm all details. We're excited to help you boost your revenue!"
    )
    
    logger.info(f"Generated meeting confirmation message for {sender_id}: {confirmation_message}")

    # In a real application, you would save this to your database
    # For now, we'll just log it.
    logger.info(f"Meeting request for sender {sender_id}: Topic='{topic}', Date='{preferred_date}', Time='{preferred_time}', Duration='{duration}'")

    # TODO: (Future) Add logic here to save to Supabase, e.g.:
    # from app.database import supabase
    # try:
    #     data, count = supabase.table('meeting_requests').insert({
    #         'sender_id': sender_id,
    #         'topic': topic,
    #         'preferred_date': preferred_date,
    #         'preferred_time': preferred_time,
    #         'duration': duration,
    #         'status': 'pending_booking'
    #     }).execute()
    #     logger.info(f"Meeting request saved to DB: {data}")
    # except Exception as e:
    #     logger.error(f"Failed to save meeting request to DB: {e}")

    return confirmation_message
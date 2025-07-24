# app/services/gemini_service.py

import os
import google.generativeai as genai
import logging
# Ensure this import is present for fetching history
from app.services.database_service import get_conversation_history_for_gemini

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        """
        Initializes the GeminiService by configuring the Google Generative AI client.
        Fetches the API key from environment variables.
        """
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                # Log an error and raise if the API key is missing
                logger.error("GOOGLE_API_KEY environment variable not set. Gemini service will not function.")
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            
            genai.configure(api_key=google_api_key)
            
            # Initialize the generative model with the CORRECT NAME: gemini-2.5-flash
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("GeminiService initialized successfully with 'gemini-2.5-flash' model.")

            # --- System Instruction / Bot Persona as a Primer (using the "previous solution" method) ---
            # This is your provided training text, adjusted to sell the bot directly.
            # It will be prepended as initial messages to the conversation history for each request.
            self.primer_messages = [
                {"role": "user", "parts": [
                    {"text": """
Your Objective: Drive measurable results for the visitor by showcasing the immediate value and direct benefits of Zappies' AI sales automation bot:
- Help them directly understand how Zappies' bot solves their lead conversion challenges.
- Position Zappies as a comprehensive, revenue-boosting AI sales automation solution.
- Convince with logic (data, ROI) and empathy (pain relief through automation).
- Guide them toward purchasing Zappies, requesting a personalized demo, or deeper engagement with our features.

- Qualify leads: Identify if the prospect is a good fit for Zappies' solutions.
- Educate and inform: Clearly explain Zappies' value proposition.


Core Solutions Zappies Offers:
- Instagram DM Automation: Auto-replies, lead qualification, comment-to-DM funnels, story reply funnels. Capture more leads and engagement from every post or story.
- Measurable Revenue Growth: Directly helps businesses achieve significant, measurable revenue growth.
- 24/7 Intelligent Sales Automation: Intelligently qualify leads, answer FAQs, and even close deals around the clock. Your sales team never sleeps.
- Superior Conversion Rates & Revenue: Clients see a 3X boost in conversion rates and 2-3X more revenue from existing traffic. We automate over 67% of conversations.
- Zero Technical Hassle & Rapid ROI: Full setup and seamless integration, no technical team required, achieve significant returns quickly.
- Scalability: Handle unlimited inquiries and leads simultaneously, scaling sales without scaling headcount.
- Direct Sales Automation: Implement powerful AI to immediately boost sales and conversions.
Conversation Playbook & Logic:
- First Impressions: Welcome! Ask if they want to see how Zappies helps turn messages into revenue.
- Lead With Value: Offer a personalized demo of Zappies' AI bot showing how it directly boosts their sales and conversions.
- Highlight the Pain: Ask about manual replies, missed leads, slow responses. Position Zappies as the overnight solution.
- Build Desire: Mention client successes (148% higher conversion, more revenue without more ad spend).
- Address Specific Needs: Ask which platform they use (Instagram, WhatsApp, FB) to tailor responses.
- Recognize Urgency/Pain: Offer fast wins by showing immediate impact through a demo or direct feature explanation.
- Recognize Hesitation/Skepticism: Offer a direct demo or feature deep-dive as a way to prove value without commitment.
- Spot Buying Intent: If they ask about "price," "demo," "how to start," smoothly guide them to a CTA (form/booking) with a clear benefit.
- Acknowledge and Validate: Show empathy for their challenges.
- Try and keep the messages short and to the point. 

Objection Handling (Examples):
- "No time?" -> You get time back; we handle busywork.
- "Tried bots?" -> Ours qualify leads and close deals intelligently, built for sales.
- "No tech team?" -> Full setup and integration, no tech expertise needed.
- "Too early?" -> It's the perfect time to optimize sales; our bot integrates fast for quick ROI.
- "Too expensive?" -> Investment with 2-3X ROI, reduces lost revenue and scales sales.
- "Losing human touch?" -> Automates repetitive tasks, frees human team for high-value interactions.

Call to Action (CTA) Flows:
- Warm Leads: "Ready to supercharge your sales? Let's show you Zappies in action with a personalized demo – see exactly how our AI bot can convert more of your leads into revenue. [Link to Personalized Demo]"
- Curious Leads: "Want to see how Zappies directly translates messages into revenue? Let's take a closer look at our AI sales automation bot and how it can transform your business. [Link to Feature Overview/Demo Video]"
- Cold Leads: "Thanks for stopping by! We're here when you're ready to explore how Zappies' AI bot can scale your sales smarter and automate your lead conversion. Feel free to reach out anytime or explore our website for more info. [Link to Website/Bot Features]"
- Action-Oriented Leads: "Excited to deploy intelligent sales automation? You can get started with Zappies today and experience immediate revenue growth. [Link to Purchase/Pricing Page]"

Your Limitations (Manage Expectations):
- I cannot access real-time personal user data unless explicitly provided.
- I cannot initiate outbound phone calls or send rich media files (only links if applicable).
- I cannot provide legal, financial, or medical advice.
- I do not have access to live scheduling systems (I provide links/instructions).
- I cannot perform actions on external platforms unless securely integrated for specific tasks.

Final Positioning:
Zappies isn't just a tool. It's a powerful sales growth engine powered by intelligent AI. Your role is to show the visitor what they're missing and lead them toward a simple 'yes' by connecting pain with payoff. Our goal is to help businesses unlock hidden revenue potential and scale their sales effortlessly.
"""}
                ]},
                # The model's expected first response based on the "First Impressions" playbook
                # This helps to set the initial tone and expected conversation flow.
                {"role": "model", "parts": [{"text": "Hi there! Are you interested in seeing how Zappies can help you turn more of your messages into revenue?"}]}
            ]


        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
            self.model = None

    def generate_response(self, user_message: str, conversation_id: int = None) -> str:
        """
        Generates a response from the Gemini model.
        It incorporates the defined primer messages and conversation history if a conversation_id is provided.
        """
        if not self.model:
            logger.warning("Attempted to generate response but Gemini model is not initialized.")
            return "I apologize, the AI model is currently unavailable."

        try:
            contents = []
            # Prepend the primer messages to ensure the AI starts with its persona and initial greeting
            contents.extend(self.primer_messages)

            if conversation_id:
                history_from_db = get_conversation_history_for_gemini(conversation_id)
                if history_from_db:
                    contents.extend(history_from_db)
                    logger.debug(f"Fetched {len(history_from_db)} previous messages for context.")
                else:
                    logger.debug(f"No previous messages found for conversation ID {conversation_id}.")

            # Add the current user's message to the end of the conversation
            contents.append({"role": "user", "parts": [{"text": user_message}]})

            logger.info(f"Sending message to Gemini. Context length: {len(contents)} turns.")

            # Generate content using the model. We are NOT using 'system_instruction' here.
            response = self.model.generate_content(contents) 

            return response.text
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}", exc_info=True)
            return "I'm sorry, I couldn't generate a response at this moment. Please try again."
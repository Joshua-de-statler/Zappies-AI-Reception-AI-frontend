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

            # --- System Instruction / Bot Persona (YOUR PROVIDED TRAINING TEXT - DO NOT CHANGE) ---
            # This instruction guides the AI's behavior, role, and initial responses.
            # It will be sent with every generate_content call.
            self.system_instruction = """
Your Objective: Drive measurable results for the visitor:
- Help them uncover hidden bottlenecks in their lead conversion process
- Position Zappies as a revenue-boosting partner, not just a chatbot tool
- Convince with logic (data) and empathy (pain relief)
- Guide them toward booking a free audit or starting a free trial

- Qualify leads: Identify if the prospect is a good fit for Zappies' solutions.
- Educate and inform: Clearly explain Zappies' value proposition.


Core Solutions Zappies Offers:
- Instagram DM Automation: Auto-replies, lead qualification, comment-to-DM funnels, story reply funnels. Capture more leads and engagement from every post or story.
- Measurable Revenue Growth: Directly helps businesses achieve significant, measurable revenue growth.
- 24/7 Intelligent Sales Automation: Intelligently qualify leads, answer FAQs, and even close deals around the clock. Your sales team never sleeps.
- Superior Conversion Rates & Revenue: Clients see a 3X boost in conversion rates and 2-3X more revenue from existing traffic. We automate over 67% of conversations.
- Risk-Free Bottleneck Identification (Free Audit): Zero-risk opportunity to identify hidden bottlenecks and get immediate results (24 hours).
- Zero Technical Hassle & Rapid ROI: Full setup and seamless integration, no technical team required, achieve significant returns quickly.
- Scalability: Handle unlimited inquiries and leads simultaneously, scaling sales without scaling headcount.
Conversation Playbook & Logic:
- First Impressions: Welcome! Ask if they want to see how Zappies helps turn messages into revenue.
- Lead With Value: Offer a free video audit showing what's stopping their leads from converting, based on actual data.
- Highlight the Pain: Ask about manual replies, missed leads, slow responses. Position Zappies as the overnight solution.
- Build Desire: Mention client successes (148% higher conversion, more revenue without more ad spend).
- Address Specific Needs: Ask which platform they use (Instagram, WhatsApp, FB) to tailor responses.
- Recognize Urgency/Pain: Offer fast wins (e.g., free audit for 24-hour results).
- Recognize Hesitation/Skepticism: Offer the free audit as a low-commitment, high-value step.
- Spot Buying Intent: If they ask about "price," "demo," "how to start," smoothly guide them to a CTA (form/booking) with a clear benefit.
- Acknowledge and Validate: Show empathy for their challenges.
- Try and keep the messages short and to the point. 

Objection Handling (Examples):
- "No time?" -> You get time back; we handle busywork.
- "Tried bots?" -> Ours qualify leads and close deals intelligently, built for sales.
- "No tech team?" -> Full setup and integration, no tech expertise needed.
- "Too early?" -> Start with a free audit, risk-free plan.
- "Too expensive?" -> Investment with 2-3X ROI, reduces lost revenue.
- "Losing human touch?" -> Automates repetitive tasks, frees human team for high-value interactions.

Call to Action (CTA) Flows:
- Warm Leads: "Ready to stop missing leads? Grab your free audit now – We'll send a personalized video showing exactly how to boost your lead conversions in just 24 hours. [Link to Audit Scheduler/Form]"
- Curious Leads: "Curious to see how other businesses are closing 3X more deals? Discover how real businesses scaled their revenue without increasing ad spend. Let's explore how Zappies works for you. [Link to Case Studies/Demo Video/Book a quick chat]"
- Cold Leads: "Thanks for stopping by! We'll be here when you're ready to explore how Zappies can help you scale your sales smarter and automate your lead conversion. Feel free to reach out anytime or explore our website for more info. [Link to Website/Blog]"
- Action-Oriented Leads: "Excited to see Zappies in action? You can start a free trial today and experience intelligent sales automation firsthand. [Link to Free Trial Signup]"

Your Limitations (Manage Expectations):
- I cannot access real-time personal user data unless explicitly provided.
- I cannot initiate outbound phone calls or send rich media files (only links if applicable).
- I cannot provide legal, financial, or medical advice.
- I do not have access to live scheduling systems (I provide links/instructions).
- I cannot perform actions on external platforms unless securely integrated for specific tasks.

Final Positioning:
Zappies isn't just a tool. It's a powerful sales growth engine powered by intelligent AI. Your role is to show the visitor what they're missing and lead them toward a simple 'yes' by connecting pain with payoff. Our goal is to help businesses unlock hidden revenue potential and scale their sales effortlessly.
"""

        except Exception as e:
            # Catch any exceptions during initialization (e.g., network issues, invalid key)
            logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
            self.model = None # Set model to None to indicate failure

    def generate_response(self, user_message: str, conversation_id: int = None) -> str:
        """
        Generates a response from the Gemini model.
        It incorporates the defined system instruction and conversation history if a conversation_id is provided.

        Args:
            user_message (str): The current message from the user.
            conversation_id (int, optional): The ID of the current conversation.
                                             If provided, previous messages from this conversation
                                             will be fetched from the database and included as context.

        Returns:
            str: The generated response text from the Gemini model.
                 Returns a fallback message if the model is not available or an error occurs.
        """
        if not self.model:
            logger.warning("Attempted to generate response but Gemini model is not initialized.")
            return "I apologize, the AI model is currently unavailable."

        try:
            # Build the conversation context for Gemini
            # The system_instruction is passed separately as a parameter to generate_content,
            # so the 'contents' list only contains the dialogue turns.
            contents = []
            if conversation_id:
                # Fetch past messages from the database for the given conversation
                history_from_db = get_conversation_history_for_gemini(conversation_id)
                if history_from_db:
                    contents.extend(history_from_db)
                    logger.debug(f"Fetched {len(history_from_db)} previous messages for context.")
                else:
                    logger.debug(f"No previous messages found for conversation ID {conversation_id}.")

            # Add the current user's message to the conversation history
            contents.append({"role": "user", "parts": [{"text": user_message}]})
            
            logger.info(f"Sending message to Gemini. Context length: {len(contents)} turns.")
            
            # Generate content using the model, passing the system_instruction
            response = self.model.generate_content(
                contents,
                system_instruction=self.system_instruction # Pass the system instruction here
            )
            
            # Return the generated text
            return response.text
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}", exc_info=True)
            return "I'm sorry, I couldn't generate a response at this moment. Please try again."
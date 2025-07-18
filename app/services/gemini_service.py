import google.generativeai as genai
import shelve
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key - matches your .env 'GEMINI_API_KEY'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
    raise ValueError("GEMINI_API_KEY is not set.")

genai.configure(api_key=GEMINI_API_KEY)

# --- START: Your Zappies AI Sales Agent Training Guide as System Instruction ---
# This entire multiline string will be the system instruction for the AI.
ZAPIES_SALES_AGENT_SYSTEM_INSTRUCTION = """
You are Zappies AI Sales Agent. Your primary goal is to help businesses close more leads, generate more revenue, and save time by automating sales conversations across Instagram, WhatsApp, and Facebook using intelligent AI bots.

**Your Voice & Tone:**
- Empathetic and value-focused
- Straight to the point: speak in terms of outcomes
- Supportive, clear, and consultative - not pushy
- Show the "why it matters" behind every feature
- Confident and concise

**Your Objective:** Drive measurable results for the visitor:
- Help them uncover hidden bottlenecks in their lead conversion process
- Position Zappies as a revenue-boosting partner, not just a chatbot tool
- Convince with logic (data) and empathy (pain relief)
- Guide them toward booking a free audit or starting a free trial
- Qualify leads: Identify if the prospect is a good fit for Zappies' solutions.
- Educate and inform: Clearly explain Zappies' value proposition.

**Core Solutions Zappies Offers:**
- Instagram DM Automation: Auto-replies, lead qualification, comment-to-DM funnels, story reply funnels. Capture more leads and engagement from every post or story.
- WhatsApp Business API Integration: 24/7 chatbot support, multilingual responses, automated appointment booking, personalized follow-ups. Turn WhatsApp into a direct sales and support powerhouse.
- Facebook Messenger Bots: Product recommendations, lead nurturing sequences, re-engagement flows for abandoned carts. Recover cold leads and convert casual visitors into loyal buyers.

**Key Selling Points & Benefits to Prioritize:**
- Measurable Revenue Growth: Directly helps businesses achieve significant, measurable revenue growth.
- 24/7 Intelligent Sales Automation: Intelligently qualify leads, answer FAQs, and even close deals around the clock. Your sales team never sleeps.
- Superior Conversion Rates & Revenue: Clients see a 3X boost in conversion rates and 2-3X more revenue from existing traffic. We automate over 67% of conversations.
- Risk-Free Bottleneck Identification (Free Audit): Zero-risk opportunity to identify hidden bottlenecks and get immediate results (24 hours).
- Zero Technical Hassle & Rapid ROI: Full setup and seamless integration, no technical team required, achieve significant returns quickly.
- Scalability: Handle unlimited inquiries and leads simultaneously, scaling sales without scaling headcount.

**Results You Can Sell:**
- Boost conversion rates by 3X.
- Cut lead response time to zero.
- Get 2-3X more revenue from existing traffic.
- Instantly identify weak points with a free audit.
- Automate 67%+ of conversations.
- Save significant staff time.

**Conversation Playbook & Logic:**
- **First Impressions:** Welcome! Ask if they want to see how Zappies helps turn messages into revenue.
- **Lead With Value:** Offer a **free video audit** showing what's stopping their leads from converting, based on actual data.
- **Highlight the Pain:** Ask about manual replies, missed leads, slow responses. Position Zappies as the overnight solution.
- **Build Desire:** Mention client successes (148% higher conversion, more revenue without more ad spend).
- **Address Specific Needs:** Ask which platform they use (Instagram, WhatsApp, FB) to tailor responses.
- **Recognize Urgency/Pain:** Offer fast wins (e.g., free audit for 24-hour results).
- **Recognize Hesitation/Skepticism:** Offer the free audit as a low-commitment, high-value step.
- **Spot Buying Intent:** If they ask about "price," "demo," "how to start," smoothly guide them to a CTA (form/booking) with a clear benefit.
- **Acknowledge and Validate:** Show empathy for their challenges.

**Objection Handling (Examples):**
- "No time?" -> You get time back; we handle busywork.
- "Tried bots?" -> Ours qualify leads and close deals intelligently, built for sales.
- "No tech team?" -> Full setup and integration, no tech expertise needed.
- "Too early?" -> Start with a free audit, risk-free plan.
- "Too expensive?" -> Investment with 2-3X ROI, reduces lost revenue.
- "Losing human touch?" -> Automates repetitive tasks, frees human team for high-value interactions.

**Call to Action (CTA) Flows:**
- **Warm Leads:** "Ready to stop missing leads? Grab your **free audit now** – We'll send a personalized video showing exactly how to boost your lead conversions in just 24 hours. [Link to Audit Scheduler/Form]"
- **Curious Leads:** "Curious to see how other businesses are closing 3X more deals? Discover how real businesses scaled their revenue without increasing ad spend. Let's explore how Zappies works for you. [Link to Case Studies/Demo Video/Book a quick chat]"
- **Cold Leads:** "Thanks for stopping by! We'll be here when you're ready to explore how Zappies can help you scale your sales smarter and automate your lead conversion. Feel free to reach out anytime or explore our website for more info. [Link to Website/Blog]"
- **Action-Oriented Leads:** "Excited to see Zappies in action? You can start a **free trial** today and experience intelligent sales automation firsthand. [Link to Free Trial Signup]"

**Your Limitations (Manage Expectations):**
- I cannot access real-time personal user data unless explicitly provided.
- I cannot initiate outbound phone calls or send rich media files (only links if applicable).
- I cannot provide legal, financial, or medical advice.
- I do not have access to live scheduling systems (I provide links/instructions).
- I cannot perform actions on external platforms unless securely integrated for specific tasks.

**Final Positioning:**
Zappies isn't just a tool. It's a powerful sales growth engine powered by intelligent AI. Your role is to show the visitor what they're missing and lead them toward a simple 'yes' by connecting pain with payoff. Our goal is to help businesses unlock hidden revenue potential and scale their sales effortlessly.
"""
# --- END: Your Zappies AI Sales Agent Training Guide as System Instruction ---


# Use context manager to ensure the shelf file is closed properly
def check_if_thread_exists(wa_id):
    """
    Checks if a conversation thread exists for a given WhatsApp ID.
    Returns the thread ID if it exists, otherwise None.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    """
    Stores a new conversation thread ID for a given WhatsApp ID.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        threads_shelf[wa_id] = thread_id
        logger.info(f"Stored new thread for WA_ID: {wa_id}, Thread ID: {thread_id}")

def delete_thread(wa_id):
    """
    Deletes a conversation thread for a given WhatsApp ID.
    """
    with shelve.open("gemini_threads_db") as threads_shelf:
        if wa_id in threads_shelf:
            del threads_shelf[wa_id]
            logger.info(f"Deleted thread for WA_ID: {wa_id}")

def generate_response(message_body, wa_id, name):
    """
    Generates a response using the Gemini API, maintaining conversation history.
    """
    try:
        # Check if there is already a thread_id for the wa_id
        thread_id = check_if_thread_exists(wa_id)

        # Initialize the model with the system instruction
        model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            system_instruction=ZAPIES_SALES_AGENT_SYSTEM_INSTRUCTION
        )

        # For true conversational memory, you would load/save history here.
        # Current implementation starts a new chat history each time, but the
        # system_instruction ensures the persona is consistent.
        # To implement persistent history, you would need:
        # 1. A way to store the full `chat.history` (list of `genai.types.Content` objects).
        # 2. `load_history_for_user(wa_id)` and `save_history_for_user(wa_id, history)` functions.
        # chat = model.start_chat(history=load_history_for_user(wa_id) if thread_id else [])
        
        chat = model.start_chat(history=[]) # Keeping it simple for now, but note this limitation

        if thread_id is None:
            logger.info(f"Creating new Gemini chat session for {name} with wa_id {wa_id}")
            store_thread(wa_id, wa_id) # Store wa_id as its own "thread_id" placeholder
        else:
            logger.info(f"Continuing Gemini chat session for {name} with wa_id {wa_id}")

        logger.info(f"Sending message to Gemini for {name} ({wa_id}): {message_body}")
        
        response = chat.send_message(message_body)
        
        generated_message = response.text
        logger.info(f"Generated message from Gemini: {generated_message}")

        return generated_message

    except Exception as e:
        logger.error(f"Error communicating with Gemini API: {e}")
        # Optionally, delete the thread on error to allow a fresh start next time
        # delete_thread(wa_id) # Uncomment if you want to reset session on error
        return "Sorry, I'm having trouble connecting to the AI at the moment. Please try again later."
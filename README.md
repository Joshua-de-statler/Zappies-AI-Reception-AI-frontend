# AI WhatsApp Bot with Python, Flask, and Gemini

This repository contains the source code for an intelligent WhatsApp chatbot. It uses the Meta Cloud API for WhatsApp integration, a Flask server to handle webhooks, a PostgreSQL database for conversation history, and Google's Gemini Pro for generating conversational AI responses.

## Features

- **Flask Backend**: A lightweight and robust web server using the factory pattern for better organization.
- **WhatsApp Cloud API Integration**: Connects directly with Meta's services to send and receive messages.
- **Gemini AI Integration**: Leverages Google's Gemini model for natural, context-aware conversations.
- **Database Persistence**: Stores conversation history in a PostgreSQL database (using Supabase in this guide), allowing the bot to remember past interactions.
- **Secure Webhooks**: Uses `X-Hub-Signature-256` verification to ensure that incoming requests are genuinely from Meta.
- **Easy Configuration**: All essential keys, tokens, and settings are managed in a single `.env` file.
- **Customizable Persona**: The bot's personality and core instructions are defined in `app/persona.py`, making it easy to adapt for different business needs without changing the core logic.

## ⚙️ Setup and Installation Guide

Follow these steps carefully to get the bot running on your local machine for development and testing.

### Step 1: Prerequisites

Before you begin, ensure you have the following:

- Python 3.8+: [Download Python](https://www.python.org/downloads/).
- `pip`: Python's package installer (usually comes with Python).
- `Git`: To clone the repository.
- `ngrok` Account: A tool to expose your local server to the internet. Sign up for a free account at [ngrok.com](https://ngrok.com) to get a static domain, which is required by Meta.
- Meta Developer Account: To create and manage your WhatsApp Business App.
- Google AI Studio Account: To get a Google API Key for the Gemini model.
- Supabase Account: For a free, cloud-hosted PostgreSQL database.

### Step 2: Clone the Repository & Install Dependencies

Open your terminal and run the following commands:

```bash
# Clone the repository
git clone [https://github.com/joshua-de-statler/naturarose-zappies.git](https://github.com/joshua-de-statler/naturarose-zappies.git)
cd naturarose-zappies

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install the required Python packages
pip install -r requirements.txt
```
### Step 3: Set Up the Supabase Database

This project uses a PostgreSQL database to store conversation history. We'll use Supabase for a quick and free setup.

1.  **Create a Supabase Project**:
    -   Go to [supabase.com](https://supabase.com), sign in, and create a new project.
    -   Note down the database password you set during creation.

2.  **Get Your Database Connection String**:
    -   In your Supabase project dashboard, navigate to **Project Settings** (the gear icon).
    -   Go to the **Database** section.
    -   Under **Connection string**, copy the URI.
    -   **Important**: Replace `[YOUR-PASSWORD]` in the copied URI with the actual database password you created. This full string will be your `DATABASE_URL`.

3.  **Create the Database Tables**:
    -   In the Supabase dashboard, go to the **SQL Editor** (the terminal icon).
    -   Click **+ New query**.
    -   Copy the entire SQL script below and paste it into the editor.
    -   Click **RUN**. This will create all the necessary tables and set up the database schema correctly.

```sql
-- Create the 'companies' table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) UNIQUE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the 'whatsapp_users' table
CREATE TABLE whatsapp_users (
    id SERIAL PRIMARY KEY,
    wa_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);
CREATE INDEX ix_whatsapp_users_wa_id ON whatsapp_users (wa_id);

-- Create the 'conversations' table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES whatsapp_users(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

-- Create the 'messages' table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    sender_type VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    response_to_message_id INTEGER REFERENCES messages(id),
    meta_message_id VARCHAR(255) UNIQUE
);
CREATE INDEX ix_messages_meta_message_id ON messages (meta_message_id);

-- Create the 'conversion_events' table
CREATE TABLE conversion_events (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    event_type VARCHAR(50) NOT NULL,
    details JSONB,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the 'bot_statistics' table
CREATE TABLE bot_statistics (
    id SERIAL PRIMARY KEY,
    company_id INTEGER UNIQUE NOT NULL REFERENCES companies(id),
    total_messages INTEGER NOT NULL DEFAULT 0,
    total_recipients INTEGER NOT NULL DEFAULT 0,
    total_conversions INTEGER NOT NULL DEFAULT 0,
    avg_response_time_ms REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the 'alembic_version' table for Flask-Migrate
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Stamp the database with the initial migration version.
-- This prevents Flask-Migrate from trying to re-create existing tables.
INSERT INTO alembic_version (version_num) VALUES ('98ad817f86d1');
```

### Step 4: Configure Environment Variables

-   In the project's root directory, find the `example.env` file.
-   Rename it to `.env`.
-   Open the new `.env` file and fill in the required values. The comments in the file explain where to find each one.

---

### Step 5: Customize the Bot's Persona

-   Open the `app/persona.py` file.
-   Modify the text inside the `PRIMER_MESSAGES` variable. This text defines the bot's identity, instructions, and knowledge base. This is where you can tailor the AI to your specific business needs.

---

### Step 6: Expose Your Local Server with ngrok

-   Follow the instructions on the ngrok dashboard to install the agent and connect your account.
-   Create a static domain in your ngrok dashboard (e.g., `example-bot.ngrok-free.app`).
-   Start `ngrok` to forward traffic to your local Flask app (which runs on port `5000` by default):

```bash
ngrok http --domain=your-static-domain.ngrok-free.app 5000
```
-    Keep this terminal window running. ngrok will display the public URL where your local server is now accessible.

### Step 7: Configure the WhatsApp Webhook

-   Go to your Meta App Dashboard.
-   Navigate to WhatsApp -> Configuration.
-   In the Webhooks section, click Edit.
-   Callback URL: Paste your full ngrok URL, followed by /webhook.
-   Example: https://example-bot.ngrok-free.app/webhook
-   Verify token: Paste the exact same VERIFY_TOKEN value you set in your .env file.
-   Click Verify and save. You should see a success message.
-   Next to "Webhook fields," click Manage.
-   Subscribe to the messages field.

### Running the Bot

Open a new terminal (leave the ngrok terminal running). Ensure your virtual environment is still active.
Start the Flask application:

```bash
flask run
```

### Project Structure
```bash
/
├── app/
│   ├── __init__.py         # Initializes the Flask app (Factory Pattern)
│   ├── config.py           # Configuration classes (loaded from .env)
│   ├── models.py           # SQLAlchemy database models
│   ├── persona.py          # The AI's personality and instructions
│   ├── views.py            # Defines the /webhook endpoint
│   ├── decorators/
│   │   └── security.py     # Webhook signature verification
│   ├── services/
│   │   ├── database_service.py # Functions for database interactions
│   │   └── gemini_service.py   # Handles communication with the Gemini API
│   └── utils/
│       └── whatsapp_utils.py # Core logic for processing messages
│
├── migrations/             # Database migration scripts (Alembic)
│
├── .env                    # (You create this) Your secret keys and config
├── example.env             # Template for the .env file
├── requirements.txt        # Python package dependencies
└── run.py                  # The main entry point to start the app
```
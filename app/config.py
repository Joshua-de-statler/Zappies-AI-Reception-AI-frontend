# app/config.py

import os
from dotenv import load_dotenv # Import load_dotenv
import logging

def configure_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_configurations(app):
    # Load environment variables from .env file located in the project root
    # 'load_dotenv()' searches for .env in the current directory and its parents.
    # Assuming run.py is in the root, this should find your .env file.
    load_dotenv(override=True) # 'override=True' ensures that variables in .env overwrite existing system env vars if they have the same name.

    # Explicitly load all relevant environment variables into Flask's config
    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")
    app.config["APP_ID"] = os.getenv("APP_ID")
    app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    app.config["RECIPIENT_WAID"] = os.getenv("RECIPIENT_WAID")
    app.config["VERSION"] = os.getenv("VERSION", "v18.0") # Default to v18.0 if not set
    app.config["PHONE_NUMBER_ID"] = os.getenv("PHONE_NUMBER_ID")
    app.config["VERIFY_TOKEN"] = os.getenv("VERIFY_TOKEN")
    app.config["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY") # <-- This is the key for Gemini

    # Database URL for Flask-SQLAlchemy
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"] # Flask-SQLAlchemy uses this key


    # --- DEBUGGING LOGS (These will show you if the keys are loaded) ---
    logging.info(f"DEBUG: GOOGLE_API_KEY loaded: {'*****' if app.config.get('GOOGLE_API_KEY') else 'None/Empty'}")
    logging.info(f"DEBUG: ACCESS_TOKEN loaded: {'*****' if app.config.get('ACCESS_TOKEN') else 'None/Empty'}")
    # --- END DEBUGGING LOGS ---


    # Ensure critical variables are set
    required_vars = ["ACCESS_TOKEN", "PHONE_NUMBER_ID", "VERIFY_TOKEN", "DATABASE_URL"]
    for var in required_vars:
        if not app.config.get(var):
            logging.error(f"Missing critical environment variable: {var}. Please check your .env file.")
            # If any critical variable is missing, you might want to raise an error
            # raise EnvironmentError(f"Missing critical environment variable: {var}")

    # Set Flask's debug mode based on environment variable (defaults to True)
    app.config.setdefault("DEBUG", os.getenv("FLASK_DEBUG", "True").lower() in ['true', '1'])
    # Set Flask's port based on environment variable (defaults to 5000)
    app.config.setdefault("PORT", int(os.getenv("PORT", 5000)))

    logging.info("Configurations loaded.")
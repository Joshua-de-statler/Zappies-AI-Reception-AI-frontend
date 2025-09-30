# app/config.py

import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'a_default_secret_key')
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # WhatsApp and Meta API credentials
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    APP_ID = os.getenv("APP_ID")
    APP_SECRET = os.getenv("APP_SECRET")
    RECIPIENT_WAID = os.getenv("RECIPIENT_WAID")
    VERSION = os.getenv("VERSION", "v20.0")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    GRAPH_API_URL = os.getenv("GRAPH_API_URL", f"https://graph.facebook.com/{VERSION}")
    
    # Google Gemini API Key and model
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # Business Logic
    CALENDLY_LINK = os.getenv("CALENDLY_LINK")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    pass

def configure_logging():
    """Configures the logging for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ensure critical variables are set
    required_vars = ["ACCESS_TOKEN", "PHONE_NUMBER_ID", "VERIFY_TOKEN", "DATABASE_URL", "GOOGLE_API_KEY", "APP_SECRET"]
    for var in required_vars:
        if not os.getenv(var):
            logging.error(f"FATAL: Missing critical environment variable: {var}. Please check your .env file.")
            # In a real app, you might want to raise an exception here
            # raise EnvironmentError(f"Missing critical environment variable: {var}")
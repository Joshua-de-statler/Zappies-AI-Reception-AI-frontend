import os
from flask import Flask
from app.config import load_configurations, configure_logging
from app.models import db # Import the SQLAlchemy database instance
# from app.views import webhook_blueprint # Import the blueprint where your webhook routes are defined

def create_app():
    """
    Factory function to create and configure the Flask application.
    This pattern allows for different configurations (e.g., testing, production).
    """
    app = Flask(__name__)

    # Load configurations from config.py and environment variables
    load_configurations(app)

    # Configure logging for the application
    configure_logging()

    # Initialize SQLAlchemy with the Flask app
    db.init_app(app)

    # Register blueprints (collections of routes and other app parts)
    # The webhook_blueprint defines your /webhook GET and POST routes
    app.register_blueprint(webhook_blueprint)

    # Create database tables if they don't exist
    # This must be done within an application context
    with app.app_context():
        db.create_all()
        # You might also add initial data creation here if needed (e.g., default company)

    # Log that the app has been created and configured
    app.logger.info("Flask application created and configured successfully.")

    return app
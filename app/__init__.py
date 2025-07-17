# app/__init__.py
import os
from flask import Flask
from app.config import load_configurations, configure_logging
from app.routes import whatsapp_blueprint
from app.models import db # Make sure this import is present

def create_app():
    app = Flask(__name__)

    # Load configurations
    load_configurations(app)

    # Configure logging
    configure_logging()

    # Initialize extensions
    db.init_app(app) # This line is crucial for Flask-SQLAlchemy

    # Register blueprints
    app.register_blueprint(whatsapp_blueprint)

    # Create database tables if they don't exist
    # This should be inside app context after db is initialized
    with app.app_context():
        db.create_all() # This creates all tables defined in app/models.py

    return app
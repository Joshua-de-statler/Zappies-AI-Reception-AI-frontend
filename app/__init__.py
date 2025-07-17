# app/__init__.py

from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from .models import db # Import the db instance

def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)

    # --- NEW DATABASE TABLE CREATION ---
    # This should ideally be handled by a migration tool (e.g., Flask-Migrate) in production
    # For initial setup, we create tables if they don't exist within the application context.
    with app.app_context():
        db.create_all()
    # --- END NEW DATABASE TABLE CREATION ---

    return app
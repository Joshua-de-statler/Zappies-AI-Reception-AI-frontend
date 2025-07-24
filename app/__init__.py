import os
from flask import Flask
from app.config import load_configurations, configure_logging
from app.models import db # Import the SQLAlchemy database instance
from app.views import webhook_blueprint
from flask_migrate import Migrate # Add this import

# Initialize Migrate outside create_app, but pass app later
migrate = Migrate() # Define it globally or pass it around

def create_app():
    app = Flask(__name__)
    load_configurations(app)
    configure_logging()
    db.init_app(app)
    migrate.init_app(app, db) # Initialize Flask-Migrate with your app and db

    app.register_blueprint(webhook_blueprint)

    with app.app_context():
        # db.create_all() # COMMENT OUT OR REMOVE THIS LINE! Migrations will handle creation/updates
        pass # Keep app_context for other potential initializations if needed

    app.logger.info("Flask application created and configured successfully.")
    return app
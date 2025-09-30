# app/__init__.py
import os
from flask import Flask
from app.config import DevelopmentConfig, ProductionConfig, configure_logging
from app.models import db
from app.views import webhook_blueprint
from flask_migrate import Migrate

migrate = Migrate()

def create_app():
    """Creates and configures an instance of the Flask application."""
    app = Flask(__name__)
    
    # Load configuration from a class
    if os.getenv('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)
        
    configure_logging()

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(webhook_blueprint)

    app.logger.info("Flask application created and configured successfully.")
    return app
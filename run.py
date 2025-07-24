# run.py
import os
from app import create_app, db # Import db as well, if you intend to run commands directly from here
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() # Load environment variables from .env file

# Log loaded configurations (for debugging, can be removed in production)
logger.info(f"DEBUG: GOOGLE_API_KEY loaded: {os.getenv('GOOGLE_API_KEY') is not None}")
logger.info(f"DEBUG: ACCESS_TOKEN loaded: {os.getenv('ACCESS_TOKEN') is not None}")
logger.info("Configurations loaded.")

app = create_app()

# Add this if you want to use 'flask db' commands
# from flask.cli import with_appcontext
# from flask_migrate import MigrateCommand
# app.cli.add_command('db', MigrateCommand) # Not strictly necessary for Railway, but for local management

if __name__ == '__main__':
    logger.info("Starting Flask application on http://0.0.0.0:5000 (Debug: False)")
    app.run(host='0.0.0.0', port=5000, debug=False)
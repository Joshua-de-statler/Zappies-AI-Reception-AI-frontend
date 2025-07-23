# app/routes.py (Complete and Final Version)
from flask import Blueprint
# Import the webhook_blueprint from views.py
from app.views import webhook_blueprint

# Create a top-level blueprint for your main application routes.
# This acts as an aggregator for other, more specific blueprints.
main_routes_blueprint = Blueprint("main_routes", __name__)

# Register the webhook blueprint onto this main blueprint.
# This means /webhook routes will be accessible through main_routes_blueprint.
main_routes_blueprint.register_blueprint(webhook_blueprint)

# If you had other blueprints (e.g., for user authentication, admin panel),
# you would register them here as well:
# from app.auth import auth_blueprint
# main_routes_blueprint.register_blueprint(auth_blueprint, url_prefix='/auth')

# This `main_routes_blueprint` will then be registered in app/__init__.py
# (though currently app/__init__.py directly registers webhook_blueprint).
# For now, if app/__init__.py directly registers webhook_blueprint, this file
# might serve as a placeholder for future route organization.
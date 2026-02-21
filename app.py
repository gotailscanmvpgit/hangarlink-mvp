from flask import Flask, render_template
from config import Config
from extensions import db, migrate, login_manager, cache, mail
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest
from routes import bp as main_bp
import os

# Define the create_app function for flexibility and testing
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    # Flask-Mail config (reads from environment, falls back to console-print mode)
    app.config.setdefault('MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
    app.config.setdefault('MAIL_PORT', int(os.environ.get('MAIL_PORT', 587)))
    app.config.setdefault('MAIL_USE_TLS', os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true')
    app.config.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
    app.config.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
    app.config.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@hangarlinks.com'))

    # Ensure all tables exist on startup (bypasses Alembic migration issues)
    with app.app_context():
        db.create_all()

    
    # Configure Login Manager
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(main_bp)

    # Global Context Processors
    @app.context_processor
    def inject_global_data():
        return {
            'app_version': 'v2.1.0',
            'stripe_publishable_key': app.config.get('STRIPE_PUBLISHABLE_KEY', ''),
            'legal_disclaimer': "HangarLinks is a platform connecting hangar owners with aircraft owners. We do not own or operate hangars."
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

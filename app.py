from flask import Flask, render_template
from config import Config
from extensions import db, migrate, login_manager, cache, mail
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest
from routes import bp as main_bp
import os

import logging
logger = logging.getLogger(__name__)

# ── Safe startup DDL patcher ──────────────────────────────────────────────────
def _safe_migrate(db):
    """
    Apply any missing columns to existing tables without Alembic.
    Uses ADD COLUMN IF NOT EXISTS (Postgres) or silently swallows errors (SQLite).
    Call this once after db.create_all() on every boot.
    """
    from sqlalchemy import text
    migrations = [
        # users table — password-reset columns added in Feb 2026
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(256)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP",
        # users table — subscription/gamification columns
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE",
        # listings table
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS featured_expires_at TIMESTAMP",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS featured_tier VARCHAR(20)",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS insurance_active BOOLEAN DEFAULT FALSE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS condition_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS likes INTEGER DEFAULT 0",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS video_url VARCHAR(255)",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS virtual_tour_url VARCHAR(255)",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS health_score INTEGER DEFAULT 0",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS checklist_completed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS availability_start DATE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS availability_end DATE",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_premium_listing BOOLEAN DEFAULT FALSE",
    ]
    with db.engine.connect() as conn:
        for ddl in migrations:
            try:
                conn.execute(text(ddl))
                conn.commit()
            except Exception as exc:
                # IF NOT EXISTS isn't supported in old SQLite — silently skip
                logger.debug(f"[migrate] skipped: {ddl[:60]}... ({exc})")
                try:
                    conn.rollback()
                except Exception:
                    pass

# ─────────────────────────────────────────────────────────────────────────────

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
        _safe_migrate(db)


    
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

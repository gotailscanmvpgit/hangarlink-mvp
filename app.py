from flask import Flask, render_template
from config import Config
from extensions import db, migrate, login_manager, cache, mail, limiter
from flask_compress import Compress
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest, Payment
from routes import bp as main_bp
from flask_recaptcha import ReCaptcha
import os
import stripe
from dotenv import load_dotenv

# Load .env file if it exists
if os.path.exists('.env'):
    print("📁 [CONFIG] Found .env file, loading...")
    load_dotenv()
else:
    print("☁️ [CONFIG] No .env file found, using system environment variables.")

# Compatibility for flask-recaptcha which may expect flask.Markup
import flask
try:
    from markupsafe import Markup
    flask.Markup = Markup
    import builtins
    builtins.Markup = Markup
except ImportError:
    pass

import logging
logger = logging.getLogger(__name__)

# Verify PORT for Railway
print("PORT from env:", os.environ.get('PORT', '5000'))

# Database initialization and migrations happen via extensions.py and create_app()




# ─────────────────────────────────────────────────────────────────────────────

# Define the create_app function for flexibility and testing
def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Database Summary Logging
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    db_type = getattr(config_class, 'DB_TYPE', 'UNKNOWN')
    
    # Anonymize logs (don't print passwords)
    safe_uri = db_uri
    if '@' in db_uri:
        safe_uri = db_uri.split('@')[1] if ':' not in db_uri.split('@')[0] else f"***@{db_uri.split('@')[1]}"

    print(f"🚀 [DB-INIT] Type: {db_type}")
    print(f"📍 [DB-INIT] Target: {safe_uri}")
    logger.warning(f"[DB-INIT] Type: {db_type} Target: {safe_uri}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    from extensions import socketio
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Enable Gzip compression
    Compress(app)
    
    app.limiter = limiter

    # Stripe Configuration
    s_key = app.config.get('STRIPE_SECRET_KEY')
    p_key = app.config.get('STRIPE_PUBLISHABLE_KEY')
    
    # Check for placeholder values
    if s_key and 'here' in s_key:
        print("⚠️ WARNING: Detected STRIPE_SECRET_KEY placeholder! Payment will fail.")
        logger.error("Detected STRIPE_SECRET_KEY placeholder!")
    
    if s_key and 'here' not in s_key:
        # Masked print for debugging live site
        masked_s = s_key[:7] + "..." + s_key[-4:] if len(s_key) > 15 else "***"
        print(f"✅ [STRIPE] Secret Key detected: {masked_s}")
        logger.info(f"Stripe Secret Key loaded: {masked_s}")
        stripe.api_key = s_key
    else:
        print("❌ [STRIPE] Secret Key is MISSING or using PLACEHOLDER.")
        logger.error("Stripe Secret Key is missing or invalid.")

    if p_key and 'here' not in p_key:
        masked_p = p_key[:7] + "..." + p_key[-4:] if len(p_key) > 15 else "***"
        print(f"✅ [STRIPE] Publishable Key detected: {masked_p}")
    else:
        print("❌ [STRIPE] Publishable Key is MISSING or using PLACEHOLDER.")

    # reCAPTCHA
    recaptcha = ReCaptcha(app=app)
    app.recaptcha = recaptcha

    # Flask-Mail config (reads from environment, falls back to console-print mode)
    app.config.setdefault('MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
    app.config.setdefault('MAIL_PORT', int(os.environ.get('MAIL_PORT', 587)))
    app.config.setdefault('MAIL_USE_TLS', os.environ.get('MAIL_USE_TLS', 'True') == 'True')

    # reCAPTCHA Keys (Should be in env)
    app.config.setdefault('RECAPTCHA_PUBLIC_KEY', os.environ.get('RECAPTCHA_PUBLIC_KEY', '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI')) # Dummy key
    app.config.setdefault('RECAPTCHA_PRIVATE_KEY', os.environ.get('RECAPTCHA_PRIVATE_KEY', '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')) # Dummy key
    app.config.setdefault('RECAPTCHA_ENABLED', os.environ.get('RECAPTCHA_ENABLED', 'True') == 'True')
    app.config.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
    app.config.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
    app.config.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@hangarlinks.com'))

    # All tables are created/updated via migrations or db.create_all() if needed
    with app.app_context():
        # Reliable startup: create tables if they don't exist
        db.create_all()

        # Dynamic Schema Patching (Zero Downtime / Render Live)
        from sqlalchemy import text, inspect
        try:
            inspector = inspect(db.engine)
            existing_cols = [c['name'] for c in inspector.get_columns('listings')]
            if 'available_sqft' not in existing_cols:
                db.session.execute(text("ALTER TABLE listings ADD COLUMN available_sqft FLOAT"))
                db.session.execute(text("UPDATE listings SET available_sqft = size_sqft WHERE available_sqft IS NULL"))
                db.session.commit()
                print("🚀 Successfully auto-migrated available_sqft column to live database.")
            else:
                # Backfill any NULLs
                db.session.execute(text("UPDATE listings SET available_sqft = size_sqft WHERE available_sqft IS NULL"))
                db.session.commit()
                print("✅ available_sqft column already exists.")
        except Exception as migrate_err:
            print(f"⚠️ Schema migration note: {migrate_err}")
            try:
                db.session.rollback()
            except Exception:
                pass

    # Load airport lat/lon lookup table from OurAirports CSV (or bundled fallback)
    from airport_coords import load_airport_coords, _COORDS_CACHE
    load_airport_coords()
    app.config['AIRPORT_COORDS'] = _COORDS_CACHE


    
    # Configure Login Manager
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as exc:
            logger.error(f"[user_loader] FAILED for user_id={user_id}: {exc}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return None

    # Register blueprints
    app.register_blueprint(main_bp)

    # Global Context Processors
    import datetime
    @app.context_processor
    def inject_global_data():
        return {
            'app_version': 'v2.2.0-secure',
            'stripe_publishable_key': app.config.get('STRIPE_PUBLISHABLE_KEY', ''),
            'legal_disclaimer': "HangarLinks is a coordination tool only. No liability for incidents, accidents, or disputes. Users responsible for compliance.",
            'safety_disclaimer': "HangarLink is a coordination tool only. No liability for incidents, accidents, or disputes. Users responsible for compliance.",
            'datetime': datetime.datetime
        }

    # ── Debug DB schema — admin-only, exposes column names for each table ──────
    @app.route('/debug-db')
    def debug_db():
        """Inspect live DB schema. Remove after confirming columns are correct."""
        from flask import request as freq, jsonify
        secret = freq.args.get('key', '')
        if secret != app.config.get('SECRET_KEY', 'no-key'):
            return 'Forbidden', 403
        from sqlalchemy import text, inspect as sa_inspect
        result = {}
        try:
            insp = sa_inspect(db.engine)
            for table in ['users', 'listings', 'bookings', 'messages', 'ad']:
                try:
                    cols = [c['name'] for c in insp.get_columns(table)]
                    result[table] = cols
                except Exception as e:
                    result[table] = f'ERROR: {e}'
            return jsonify({'schema': result, 'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        try:
            return render_template('404.html'), 404
        except Exception:
            return '<h2>404 — Page not found</h2><a href="/">Home</a>', 404

    @app.errorhandler(500)
    def internal_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            return render_template('500.html'), 500
        except Exception:
            return '<h2>500 — Internal Server Error</h2><a href="/">Home</a>', 500

    return app


# Module-level app instance for Gunicorn (app:app) and direct import.
# run.py should import this rather than calling create_app() again.
app = create_app()

if __name__ == '__main__':
    from extensions import socketio
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True, allow_unsafe_werkzeug=True)



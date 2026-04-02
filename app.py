import os
from dotenv import load_dotenv

# ── Load Envs First ──────────────────────────────────────────────
if os.path.exists('.env'):
    print("[CONFIG] Found .env file, loading...")
    load_dotenv()
else:
    print("[CONFIG] No .env file found, using system environment variables.")

from flask import Flask, render_template
from config import Config
from extensions import db, migrate, login_manager, cache, mail, limiter
from flask_compress import Compress
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest, Payment
from routes import bp as main_bp
from flask_recaptcha import ReCaptcha
import stripe
import cloudinary
import cloudinary.uploader
import cloudinary.api
import flask

# Compatibility for flask-recaptcha which may expect flask.Markup
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

    print(f"[DB-INIT] Type: {db_type}")
    print(f"[DB-INIT] Target: {safe_uri}")
    logger.warning(f"[DB-INIT] Type: {db_type} Target: {safe_uri}")

    # ── Mail Server Config (SendPulse, Google, etc) ─────────────────────────
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
    
    # Priority: 1. MAIL_USERNAME, 2. GMAIL_USERNAME (legacy), 3. SENDPULSE_USERNAME (custom)
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') or \
                                 os.environ.get('GMAIL_USERNAME') or \
                                 os.environ.get('SENDPULSE_USERNAME', '')
    
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') or \
                                 os.environ.get('GMAIL_APP_PASSWORD') or \
                                 os.environ.get('SENDPULSE_PASSWORD', '')
                                 
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@tryhangarlinks.com')

    # Log mail configuration for troubleshooting (masked)
    _mu = app.config.get('MAIL_USERNAME')
    print(f"[MAIL-INIT] Server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']} (TLS={app.config['MAIL_USE_TLS']})")
    print(f"[MAIL-INIT] User: {_mu if _mu else '(NOT CONFIGURED - FALLBACK TO CONSOLE)'}")


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
        print(f"[STRIPE] Secret Key detected: {masked_s}")
        logger.info(f"Stripe Secret Key loaded: {masked_s}")
        stripe.api_key = s_key
    else:
        print("[STRIPE] Secret Key is MISSING or using PLACEHOLDER.")
        logger.error("Stripe Secret Key is missing or invalid.")

    if p_key and 'here' not in p_key:
        masked_p = p_key[:7] + "..." + p_key[-4:] if len(p_key) > 15 else "***"
        print(f"[STRIPE] Publishable Key detected: {masked_p}")
    else:
        print("[STRIPE] Publishable Key is MISSING or using PLACEHOLDER.")

    # Cloudinary Configuration
    c_cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    c_api_key = os.environ.get('CLOUDINARY_API_KEY')
    c_api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    if c_cloud_name and c_api_key and c_api_secret:
        cloudinary.config(
            cloud_name=c_cloud_name,
            api_key=c_api_key,
            api_secret=c_api_secret,
            secure=True
        )
        print("[CLOUDINARY] Configured successfully.")
        logger.info("Cloudinary configured.")
    else:
        print("⚠️ [CLOUDINARY] Missing API Keys! Uploads may fail if routing to Cloudinary.")

    # reCAPTCHA
    recaptcha = ReCaptcha(app=app)
    app.recaptcha = recaptcha

    # reCAPTCHA Keys (Should be in env)
    app.config.setdefault('RECAPTCHA_PUBLIC_KEY', os.environ.get('RECAPTCHA_PUBLIC_KEY', '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI')) # Dummy key
    app.config.setdefault('RECAPTCHA_PRIVATE_KEY', os.environ.get('RECAPTCHA_PRIVATE_KEY', '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')) # Dummy key
    app.config.setdefault('RECAPTCHA_ENABLED', os.environ.get('RECAPTCHA_ENABLED', 'False') == 'True')

    # ── Self-Heal Database Schema (Railway/Postgres Strategy) ──
    with app.app_context():
        try:
            from sqlalchemy import inspect as sa_inspect, text
            insp = sa_inspect(db.engine)
            if 'listings' in insp.get_table_names():
                columns = [c['name'] for c in insp.get_columns('listings')]
                
                # Columns to add if missing
                missing = []
                if 'public_location_description' not in columns:
                    missing.append("public_location_description TEXT")
                if 'private_access_instructions' not in columns:
                    missing.append("private_access_instructions TEXT")
                    
                if missing:
                    print(f"[DB-REPAIR] Adding missing columns to listings: {missing}")
                    for col_def in missing:
                        try:
                            # Use text() to safely execute the ALTER TABLE command
                            col_name = col_def.split()[0]
                            db.session.execute(text(f"ALTER TABLE listings ADD COLUMN {col_name} TEXT"))
                            db.session.commit()
                            print(f"✅ [DB-REPAIR] Added column: {col_name}")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ [DB-REPAIR] Failed to add {col_name}: {e}")
            
            db.create_all()
            print("✅ [DB] Schema check & db.create_all() completed.")
        except Exception as create_err:
            print(f"❌ [DB] Self-heal FAILED: {create_err}")
            import traceback
            traceback.print_exc()

    @app.context_processor
    def utility_processor():
        def optimized_img(photo_filename, w=800, h=600):
            if not photo_filename:
                return ""
            if photo_filename.startswith('http'):
                return photo_filename.replace('/upload/', f'/upload/w_{w},h_{h},c_fill,f_webp/')
            else:
                from flask import url_for
                return url_for('static', filename='uploads/listings/' + photo_filename)
        return dict(optimized_img=optimized_img)

    # Load airport lat/lon lookup table
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

    # ── Health Check ──
    @app.route('/healthz')
    def healthz():
        """Bare-minimum health check."""
        import traceback
        status = {'alive': True, 'version': 'v2.2.0-secure'}
        try:
            from sqlalchemy import text, inspect as sa_inspect
            insp = sa_inspect(db.engine)
            tables = insp.get_table_names()
            status['tables'] = tables
            status['db'] = 'ok'
        except Exception as e:
            status['db'] = f'error: {e}'
            status['traceback'] = traceback.format_exc()
        from flask import jsonify
        return jsonify(status)

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

# Module-level app instance
app = create_app()

if __name__ == '__main__':
    from extensions import socketio
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True, allow_unsafe_werkzeug=True)

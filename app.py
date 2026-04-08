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
from extensions import db, migrate, login_manager, cache, mail, limiter, oauth
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

    # 🔐 OAuth Registration (New for Social Login)
    oauth.init_app(app)
    
    # Google OAuth Client
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    # Apple OAuth Client
    oauth.register(
        name='apple',
        client_id=app.config.get('APPLE_CLIENT_ID'),
        client_secret=app.config.get('APPLE_CLIENT_SECRET'),
        server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'name email'
        }
    )
    
    print("[OAUTH] Google & Apple clients registered.")

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
                if 'tail_height_clearance' not in columns:
                    missing.append("tail_height_clearance FLOAT")
                if 'price_night' not in columns:
                    missing.append("price_night FLOAT")
                if 'min_stay_nights' not in columns:
                    missing.append("min_stay_nights INTEGER DEFAULT 1")
                if 'is_premium_listing' not in columns:
                    missing.append("is_premium_listing BOOLEAN DEFAULT FALSE")
                if 'is_featured' not in columns:
                    missing.append("is_featured BOOLEAN DEFAULT FALSE")
                if 'is_verified' not in columns:
                    missing.append("is_verified BOOLEAN DEFAULT FALSE")
                if 'lat' not in columns:
                    missing.append("lat FLOAT")
                if 'lon' not in columns:
                    missing.append("lon FLOAT")
                if 'is_heated' not in columns:
                    missing.append("is_heated BOOLEAN DEFAULT FALSE")
                if 'access_24_7' not in columns:
                    missing.append("access_24_7 BOOLEAN DEFAULT FALSE")
                if 'door_type' not in columns:
                    missing.append("door_type TEXT")
                if 'nfpa_409_compliant' not in columns:
                    missing.append("nfpa_409_compliant BOOLEAN DEFAULT FALSE")
                if 'gpu_power_available' not in columns:
                    missing.append("gpu_power_available BOOLEAN DEFAULT FALSE")
                if 'is_reported' not in columns:
                    missing.append("is_reported BOOLEAN DEFAULT FALSE")
                if 'report_count' not in columns:
                    missing.append("report_count INTEGER DEFAULT 0")
                if 'report_reason' not in columns:
                    missing.append("report_reason TEXT")
                if 'health_score' not in columns:
                    missing.append("health_score INTEGER DEFAULT 0")
                if 'condition_verified' not in columns:
                    missing.append("condition_verified BOOLEAN DEFAULT FALSE")
                if 'checklist_completed' not in columns:
                    missing.append("checklist_completed BOOLEAN DEFAULT FALSE")
                if 'insurance_active' not in columns:
                    missing.append("insurance_active BOOLEAN DEFAULT FALSE")
                if 'order_val' not in columns:
                    missing.append("order_val INTEGER DEFAULT 0")
                if 'is_verified' not in columns:
                    missing.append("is_verified BOOLEAN DEFAULT FALSE")
                if 'availability_start' not in columns:
                    missing.append("availability_start DATE")
                if 'availability_end' not in columns:
                    missing.append("availability_end DATE")
                    
                # Drop NOT NULL constraint if it exists (2026 Strategy: price_month is optional)
                try:
                    # Generic PG syntax for making column nullable
                    db.session.execute(text("ALTER TABLE listings ALTER COLUMN price_month DROP NOT NULL"))
                    # Also handle price_week if it exists
                    if 'price_week' in columns:
                        db.session.execute(text("ALTER TABLE listings ALTER COLUMN price_week DROP NOT NULL"))
                    db.session.commit()
                    print("✅ [DB-REPAIR] Made price_month and price_week nullable")
                except Exception as e:
                    db.session.rollback()
                    # Skip print for SQLite or other DBs where this syntax fails but isn't needed
                    if "syntax error" not in str(e).lower():
                        print(f"⚠️ [DB-REPAIR] Nullability update: {e}")

                if missing:
                    print(f"[DB-REPAIR] Adding missing columns to listings: {missing}")
                    for col_def in missing:
                        try:
                            # Use text() to safely execute the ALTER TABLE command
                            parts = col_def.split()
                            col_name = parts[0]
                            col_type = " ".join(parts[1:])
                            db.session.execute(text(f"ALTER TABLE listings ADD COLUMN {col_name} {col_type}"))
                            db.session.commit()
                            print(f"✅ [DB-REPAIR] Added column: {col_name}")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ [DB-REPAIR] Failed to add {col_name}: {e}")

            # Check Ad table
            if 'ad' in insp.get_table_names():
                ad_cols = [c['name'] for c in insp.get_columns('ad')]
                missing_ad = []
                if 'placement' not in ad_cols:
                    missing_ad.append("placement VARCHAR(50)")
                if 'active' not in ad_cols:
                    missing_ad.append("active BOOLEAN DEFAULT TRUE")
                if 'impressions' not in ad_cols:
                    missing_ad.append("impressions INTEGER DEFAULT 0")
                if 'clicks' not in ad_cols:
                    missing_ad.append("clicks INTEGER DEFAULT 0")
                
                if missing_ad:
                    print(f"[DB-REPAIR] Adding missing columns to ad: {missing_ad}")
                    for col_def in missing_ad:
                        try:
                            parts = col_def.split()
                            col_name = parts[0]
                            col_type = " ".join(parts[1:])
                            db.session.execute(text(f"ALTER TABLE ad ADD COLUMN {col_name} {col_type}"))
                            db.session.commit()
                            print(f"✅ [DB-REPAIR] Added ad column: {col_name}")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ [DB-REPAIR] Failed to add ad column {col_name}: {e}")

            # Check users table
            if 'users' in insp.get_table_names():
                missing_user = []
                user_cols = [c['name'] for c in insp.get_columns('users')]
                if 'saved_aircraft' not in user_cols:
                    missing_user.append("saved_aircraft VARCHAR(100)")
                if 'total_revenue' not in user_cols:
                    missing_user.append("total_revenue FLOAT DEFAULT 0.0")
                if 'is_premium' not in user_cols:
                    missing_user.append("is_premium BOOLEAN DEFAULT FALSE")
                if 'role' not in user_cols:
                    missing_user.append("role VARCHAR(20) DEFAULT 'renter'")
                if 'profile_pic' not in user_cols:
                    missing_user.append("profile_pic VARCHAR(255)")
                if 'is_verified' not in user_cols:
                    missing_user.append("is_verified BOOLEAN DEFAULT FALSE")
                
                if missing_user:
                    print(f"[DB-REPAIR] Adding missing columns to users: {missing_user}")
                    for col_def in missing_user:
                        try:
                            parts = col_def.split()
                            col_name = parts[0]
                            col_type = " ".join(parts[1:])
                            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                            db.session.commit()
                            print(f"✅ [DB-REPAIR] Added user column: {col_name}")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ [DB-REPAIR] Failed to add user column {col_name}: {e}")
                
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
    from werkzeug.middleware.proxy_fix import ProxyFix
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

    # Secure for Proxies (Railway/Render SSL)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    return app

# Module-level app instance
app = create_app()

if __name__ == '__main__':
    from extensions import socketio
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True, allow_unsafe_werkzeug=True)

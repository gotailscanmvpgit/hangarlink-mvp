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
    print("[CONFIG] Found .env file, loading...")
    load_dotenv()
else:
    print("[CONFIG] No .env file found, using system environment variables.")

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

    print(f"[DB-INIT] Type: {db_type}")
    print(f"[DB-INIT] Target: {safe_uri}")
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
    app.config.setdefault('RECAPTCHA_ENABLED', os.environ.get('RECAPTCHA_ENABLED', 'False') == 'True')
    app.config.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
    app.config.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
    app.config.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@hangarlinks.com'))

    # All tables are created/updated via migrations or db.create_all() if needed
    with app.app_context():
        # ── Step 1: Create all tables (safe for both SQLite and PostgreSQL) ──
        try:
            db.create_all()
            print("✅ [DB] db.create_all() completed — all model tables ensured.")
        except Exception as create_err:
            # Log loudly but DON'T crash — routes self-heal on first request
            print(f"❌ [DB] db.create_all() FAILED (app will self-heal per-request): {create_err}")
            import traceback
            traceback.print_exc()

        # ── Step 2: Dynamic column patching (add any missing columns) ──
        from sqlalchemy import text, inspect as sa_inspect
        try:
            inspector = sa_inspect(db.engine)
            is_postgres = 'postgresql' in str(db.engine.url).lower()

            def safe_add_column(table, col_name, col_type):
                """Add a column if it doesn't already exist. PG-safe."""
                try:
                    existing = [c['name'] for c in inspector.get_columns(table)]
                    if col_name not in existing:
                        db.session.execute(text(
                            f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                        ))
                        db.session.commit()
                        print(f"  ✅ Added {table}.{col_name}")
                except Exception as col_err:
                    db.session.rollback()
                    # PostgreSQL raises if column already exists — safe to ignore
                    errmsg = str(col_err).lower()
                    if 'already exists' in errmsg or 'duplicate column' in errmsg:
                        print(f"  ℹ️  {table}.{col_name} already exists (skipped)")
                    else:
                        print(f"  ⚠️  Could not add {table}.{col_name}: {col_err}")

            # --- Listings ---
            for col_name, col_type in [
                ('available_sqft', 'FLOAT'),
                ('price_night', 'FLOAT DEFAULT 0.0'),
                ('min_stay_nights', 'INTEGER DEFAULT 1'),
                ('door_type', 'TEXT'),
                ('access_24_7', 'BOOLEAN DEFAULT FALSE'),
                ('is_heated', 'BOOLEAN DEFAULT FALSE'),
                ('battery_tender', 'BOOLEAN DEFAULT FALSE'),
                ('engine_heater', 'BOOLEAN DEFAULT FALSE'),
                ('snow_removal', 'BOOLEAN DEFAULT FALSE'),
                ('hurricane_tiedowns', 'BOOLEAN DEFAULT FALSE'),
                ('ramp_cam_url', 'TEXT'),
                ('tail_height_clearance', 'FLOAT'),
                ('nfpa_409_compliant', 'BOOLEAN DEFAULT FALSE'),
                ('floor_loading_pcn', 'TEXT'),
                ('gpu_power_available', 'BOOLEAN DEFAULT FALSE'),
                ('shuttle_info', 'VARCHAR(255)'),
                ('is_verified', 'BOOLEAN DEFAULT FALSE'),
            ]:
                safe_add_column('listings', col_name, col_type)

            # Backfill available_sqft
            try:
                db.session.execute(text(
                    "UPDATE listings SET available_sqft = size_sqft "
                    "WHERE available_sqft IS NULL"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()

            # --- Bookings ---
            for col_name, col_type in [
                ('owner_signed', 'BOOLEAN DEFAULT FALSE'),
                ('renter_signed', 'BOOLEAN DEFAULT FALSE'),
                ('lease_pdf_path', 'TEXT'),
                ('sign_token_owner', 'TEXT'),
                ('sign_token_renter', 'TEXT'),
            ]:
                safe_add_column('bookings', col_name, col_type)

            # --- Messages (guest messaging) ---
            for col_name, col_type in [
                ('is_guest', 'BOOLEAN DEFAULT FALSE'),
                ('guest_email', 'VARCHAR(120)'),
                ('is_flagged', 'BOOLEAN DEFAULT FALSE'),
                ('flag_reason', 'VARCHAR(100)'),
            ]:
                safe_add_column('messages', col_name, col_type)

            # --- Users ---
            for col_name, col_type in [
                ('total_revenue', 'FLOAT DEFAULT 0.0'),
                ('first_name', 'VARCHAR(50)'),
                ('last_name', 'VARCHAR(50)'),
            ]:
                safe_add_column('users', col_name, col_type)

            print("🚀 [DB] Schema migration complete.")
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

    # ── Health Check — Railway uses this to verify the app is alive ──────
    @app.route('/healthz')
    def healthz():
        """Bare-minimum health check that bypasses all DB logic."""
        import traceback
        status = {'alive': True, 'version': 'v2.2.0-secure'}
        try:
            from sqlalchemy import text, inspect as sa_inspect
            insp = sa_inspect(db.engine)
            tables = insp.get_table_names()
            status['tables'] = tables
            if 'listings' in tables:
                cols = [c['name'] for c in insp.get_columns('listings')]
                status['listing_columns'] = cols
                status['has_available_sqft'] = 'available_sqft' in cols
                count = db.session.execute(text("SELECT COUNT(*) FROM listings")).scalar()
                status['listing_count'] = count
            status['db'] = 'ok'
        except Exception as e:
            status['db'] = f'error: {e}'
            status['traceback'] = traceback.format_exc()
        from flask import jsonify
        return jsonify(status)

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

    # ── Emergency DB init — force create_all() from browser ──────────────
    @app.route('/init-db')
    def init_db_route():
        """Emergency: force db.create_all(). Requires SECRET_KEY as query param."""
        from flask import request as freq, jsonify
        import traceback
        secret = freq.args.get('key', '')
        if secret != app.config.get('SECRET_KEY', 'no-key'):
            return 'Forbidden — pass ?key=YOUR_SECRET_KEY', 403
        result = {
            'db_url': str(db.engine.url).replace(
                str(db.engine.url).split('@')[0] if '@' in str(db.engine.url) else '',
                '***'
            ),
        }
        try:
            db.create_all()
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(db.engine)
            tables = insp.get_table_names()
            result['status'] = 'ok'
            result['tables'] = tables
            result['table_count'] = len(tables)
            print(f"✅ [init-db] Tables after create_all: {tables}")
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            print(f"❌ [init-db] FAILED: {e}")
        return jsonify(result)

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



from flask import Flask, render_template
from config import Config
from extensions import db, migrate, login_manager, cache, mail
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest
from routes import bp as main_bp
import os

import logging
logger = logging.getLogger(__name__)

# Verify PORT for Railway
print("PORT from env:", os.environ.get('PORT', '5000'))

# ── Safe startup DDL patcher ──────────────────────────────────────────────────
def _safe_migrate(db):
    """
    Apply every missing column to existing production tables.
    Logs at WARNING level so output is visible in Railway/Gunicorn.
    Uses ADD COLUMN IF NOT EXISTS (Postgres 9.6+).
    SQLite silently swallows the IF NOT EXISTS on older versions.
    """
    from sqlalchemy import text

    # ALL columns across all model classes — add to this list whenever
    # you add a new db.Column to any model.
    migrations = [
        # ── users ──────────────────────────────────────────────────────
        ("users", "alert_enabled",          "BOOLEAN DEFAULT FALSE"),
        ("users", "alert_airport",          "VARCHAR(4)"),
        ("users", "alert_max_price",        "FLOAT"),
        ("users", "alert_min_size",         "INTEGER"),
        ("users", "alert_covered_only",     "BOOLEAN DEFAULT FALSE"),
        ("users", "reputation_score",       "FLOAT DEFAULT 5.0"),
        ("users", "rentals_count",          "INTEGER DEFAULT 0"),
        ("users", "is_premium",             "BOOLEAN DEFAULT FALSE"),
        ("users", "subscription_tier",      "VARCHAR(20) DEFAULT 'free'"),
        ("users", "stripe_customer_id",     "VARCHAR(100)"),
        ("users", "stripe_subscription_id", "VARCHAR(100)"),
        ("users", "subscription_expires",   "TIMESTAMP"),
        ("users", "has_analytics_access",   "BOOLEAN DEFAULT FALSE"),
        ("users", "analytics_expires_at",   "TIMESTAMP"),
        ("users", "is_admin",               "BOOLEAN DEFAULT FALSE"),
        ("users", "search_count_today",     "INTEGER DEFAULT 0"),
        ("users", "search_reset_date",      "DATE"),
        ("users", "points",                 "INTEGER DEFAULT 0"),
        ("users", "referral_code",          "VARCHAR(20)"),
        ("users", "referred_by_id",         "INTEGER"),
        ("users", "is_certified",           "BOOLEAN DEFAULT FALSE"),
        ("users", "seasonal_alerts",        "BOOLEAN DEFAULT TRUE"),
        ("users", "reset_token",            "VARCHAR(256)"),
        ("users", "reset_token_expires",    "TIMESTAMP"),
        # ── listings ───────────────────────────────────────────────────
        ("listings", "updated_at",           "TIMESTAMP"),
        ("listings", "is_featured",          "BOOLEAN DEFAULT FALSE"),
        ("listings", "featured_expires_at",  "TIMESTAMP"),
        ("listings", "featured_tier",        "VARCHAR(20)"),
        ("listings", "insurance_active",     "BOOLEAN DEFAULT FALSE"),
        ("listings", "condition_verified",   "BOOLEAN DEFAULT FALSE"),
        ("listings", "likes",                "INTEGER DEFAULT 0"),
        ("listings", "video_url",            "VARCHAR(255)"),
        ("listings", "virtual_tour_url",     "VARCHAR(255)"),
        ("listings", "health_score",         "INTEGER DEFAULT 0"),
        ("listings", "checklist_completed",  "BOOLEAN DEFAULT FALSE"),
        ("listings", "availability_start",   "DATE"),
        ("listings", "availability_end",     "DATE"),
        ("listings", "is_premium_listing",   "BOOLEAN DEFAULT FALSE"),
        ("listings", "lat",                  "FLOAT"),
        ("listings", "lon",                  "FLOAT"),
        # ── bookings ───────────────────────────────────────────────────
        ("bookings", "insurance_opt_in",     "BOOLEAN DEFAULT FALSE"),
        ("bookings", "insurance_fee",        "FLOAT DEFAULT 0.0"),
        ("bookings", "owner_rating",         "INTEGER"),
        ("bookings", "renter_rating",        "INTEGER"),
        ("bookings", "owner_review",         "TEXT"),
        ("bookings", "renter_review",        "TEXT"),
        # ── messages ───────────────────────────────────────────────────
        ("messages", "is_guest",             "BOOLEAN DEFAULT FALSE"),
        ("messages", "guest_email",          "VARCHAR(120)"),
    ]

    applied = skipped = already_exists = 0
    is_sqlite = db.engine.dialect.name == "sqlite"
    is_postgres = db.engine.dialect.name in ("postgresql", "postgres")

    logger.warning(f"[DB-MIGRATE] starting on {db.engine.dialect.name} — {len(migrations)} column checks")

    for table, column, col_type in migrations:
        try:
            if is_sqlite:
                # SQLite: PRAGMA table_info returns existing columns — no IF NOT EXISTS needed
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"PRAGMA table_info({table})"))
                    existing = {row[1] for row in result}  # row[1] = column name
                if column in existing:
                    already_exists += 1
                    continue
                # Column is missing — add it (no IF NOT EXISTS, plain ADD COLUMN)
                with db.engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    conn.commit()
                applied += 1
                logger.warning(f"[DB-MIGRATE] ✓ added {table}.{column}")

            else:
                # Postgres / other: IF NOT EXISTS is safe and atomic
                autocommit_engine = db.engine.execution_options(isolation_level="AUTOCOMMIT")
                with autocommit_engine.connect() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
                    ))
                applied += 1
                logger.warning(f"[DB-MIGRATE] ✓ added {table}.{column}")

        except Exception as exc:
            skipped += 1
            logger.warning(f"[DB-MIGRATE] ✗ {table}.{column}: {str(exc)[:100]}")

    logger.warning(
        f"[DB-MIGRATE] done — {applied} added, {already_exists} already present, "
        f"{skipped} errors out of {len(migrations)} checks"
    )




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
    @app.context_processor
    def inject_global_data():
        return {
            'app_version': 'v2.1.0',
            'stripe_publishable_key': app.config.get('STRIPE_PUBLISHABLE_KEY', ''),
            'legal_disclaimer': "HangarLinks is a platform connecting hangar owners with aircraft owners. We do not own or operate hangars."
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))



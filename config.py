import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-prod'
    
    # Priority order for Database URI:
    # 1. DATABASE_URL (Standard)
    # 2. DATABASE_PRIVATE_URL (Railway Private)
    # 3. POSTGRES_URL (Alternative name)
    # 4. Local SQLite (fallback)
    raw_db_url = os.environ.get('DATABASE_URL') or \
                 os.environ.get('DATABASE_PRIVATE_URL') or \
                 os.environ.get('POSTGRES_URL')
    
    # Log all available environment keys (not values) for debugging
    print(f"DEBUG: Available Env Keys: {list(os.environ.keys())}")
    
    if raw_db_url:
        # Standardize for SQLAlchemy
        if raw_db_url.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = raw_db_url.replace("postgres://", "postgresql://", 1)
        else:
            SQLALCHEMY_DATABASE_URI = raw_db_url
        DB_TYPE = "POSTGRESQL"
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///hangarlink.db'
        DB_TYPE = "SQLITE (EPHEMERAL - DATA WILL BE LOST ON REDEPLOY)"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ... rest of the config ...
    
    # Uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Stripe
    STRIPE_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_secret_key = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Application
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

    # Airport Data (Loaded on startup in app.py)
    # Accessible via current_app.config['AIRPORT_COORDS']
    AIRPORT_COORDS = {} 

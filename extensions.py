from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")

try:
    from flask_mail import Mail
    mail = Mail()
except ImportError:
    # Flask-Mail not installed yet - mail features will fall back to console logging
    class Mail:
        def init_app(self, app): pass
        def send(self, msg): pass
    mail = Mail()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

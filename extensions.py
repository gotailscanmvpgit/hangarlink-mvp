from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache

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

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(cors_allowed_origins="*")
except ImportError:
    class DummySocketIO:
        def init_app(self, app, **kwargs): pass
        def on(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def emit(self, *args, **kwargs): pass
        def run(self, app, **kwargs): 
            app.run(host=kwargs.get('host'), port=kwargs.get('port'), debug=kwargs.get('debug'))
    socketio = DummySocketIO()
    print("Warning: flask_socketio not installed. Real-time chat disabled.")

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

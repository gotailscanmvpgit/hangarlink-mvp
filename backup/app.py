from flask import Flask
from flask_migrate import Migrate
from extensions import db, login_manager
import os

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database Configuration (Postgres Only)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# Handle Postgres dialect fix for Render/Railway (postgres:// vs postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

if not app.config['SQLALCHEMY_DATABASE_URI']:
    print("WARNING: DATABASE_URL not set in environment. App may crash.")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY', '')
app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models
from models import User, Listing, Message, Booking

# Context processor for legal disclaimer
@app.context_processor
def inject_legal():
    with open('planning/legal-disclaimers.txt', 'r') as f:
        disclaimer = f.read()
    return {
        'legal_disclaimer': disclaimer,
        'app_version': 'v1.0.0',
        'stripe_publishable_key': app.config['STRIPE_PUBLISHABLE_KEY']
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables on startup (Disabled: Use Flask-Migrate 'flask db upgrade')
# with app.app_context():
#     db.create_all()
#     print("✅ Database tables initialized")

# Import routes/views (Direct import at end of file)
from views import *

if __name__ == '__main__':
    # Use 'flask db upgrade' for production migrations instead of create_all()
    # with app.app_context():
    #     db.create_all()
    
    # Run configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

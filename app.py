from flask import Flask
from extensions import db, login_manager
import os

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hangarlink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models
from models import User, Listing, Message

# Context processor for legal disclaimer
@app.context_processor
def inject_legal():
    with open('planning/legal-disclaimers.txt', 'r') as f:
        disclaimer = f.read()
    return {
        'legal_disclaimer': disclaimer,
        'app_version': 'v1.0.0'
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables on startup (important for Render deployment)
with app.app_context():
    db.create_all()
    print("✅ Database tables initialized")

# Import routes
from routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

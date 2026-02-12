"""
Standalone database initialization for Render.
This must run BEFORE the app starts.
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create minimal app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hangarlink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db
db = SQLAlchemy(app)

# Import models to register them
from models import User, Listing, Message, Booking

# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully!")
    print(f"📍 Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")

"""
Database initialization script for Render deployment.
Run this once to create all tables.
"""
from app import app, db

with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")

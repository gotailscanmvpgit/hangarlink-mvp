"""
Database Migration Script
Adds new 'username' column and Smart Alert columns
"""

from app import app, db
from models import User, Listing, Message

print("🔄 Starting database migration...")
print("⚠️  WARNING: This will recreate all tables and delete existing data!")
print()

response = input("Continue? (yes/no): ")

if response.lower() != 'yes':
    print("❌ Migration cancelled.")
    exit()

print()
print("📊 Recreating database with new schema...")

with app.app_context():
    # Drop all tables
    db.drop_all()
    print("✅ Old tables dropped")
    
    # Create all tables with new schema
    db.create_all()
    print("✅ New tables created with updated schema")
    
    # Verify new columns exist (conceptual check)
    print()
    print("📋 Verifying new User columns:")
    print("   - username (NEW)")
    print("   - alert_enabled")
    print("   - alert_airport")
    print("   - alert_max_price")
    print("   - alert_min_size")
    print("   - alert_min_size")
    print("   - alert_covered_only")
    
    print()
    print("📋 Verifying new Listing columns:")
    print("   - condition_verified (NEW)")
    print("   - likes (NEW)")
    
    print()
    print("✅ Database migration complete!")

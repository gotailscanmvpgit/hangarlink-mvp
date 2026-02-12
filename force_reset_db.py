from app import app
from extensions import db
from models import User, Listing, Booking, Message
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Database reset complete!")
    
    # 1. Create Admin (Certified Owner)
    admin = User(username='Admin', email='admin@hangarlink.com', 
                 password_hash=generate_password_hash('password'), role='owner',
                 is_premium=True, is_certified=True, points=1000,
                 reputation_score=5.0,
                 alert_enabled=True, alert_airport='KJFK', alert_max_price=5000)
    db.session.add(admin)
    
    # 2. Create Regular Owner
    owner = User(username='PilotDave', email='dave@example.com',
                 password_hash=generate_password_hash('password'), role='owner',
                 is_premium=False, is_certified=False, points=50,
                 reputation_score=4.2)
    db.session.add(owner)
    
    # 3. Create Renter
    renter = User(username='RenterSarah', email='sarah@example.com',
                  password_hash=generate_password_hash('password'), role='renter',
                  points=0)
    db.session.add(renter)
    
    db.session.commit()
    print("Users created.")
    
    # 4. Create Listings
    # - Listing 1: KJFK (Certified, Virtual Tour) -> High Match for Admin
    l1 = Listing(
        airport_icao='KJFK',
        size_sqft=3000,
        covered=True,
        price_month=1500.0,
        description="Premium heated hangar with 24/7 access and lounge.",
        owner_id=admin.id,
        status='Active',
        condition_verified=True,
        checklist_completed=True,
        health_score=95,
        virtual_tour_url='https://matterport.com/discover/space/example',
        availability_start=datetime.now().date(),
        created_at=datetime.now()
    )
    db.session.add(l1)
    
    # - Listing 2: KLAX (Regular Owner)
    l2 = Listing(
        airport_icao='KLAX',
        size_sqft=1200,
        covered=False, # Tie-down
        price_month=450.0,
        description="Secure tie-down spot near FBO.",
        owner_id=owner.id,
        status='Active',
        health_score=60,
        created_at=datetime.now() - timedelta(days=2)
    )
    db.session.add(l2)
    
    db.session.commit()
    print("Listings created.")

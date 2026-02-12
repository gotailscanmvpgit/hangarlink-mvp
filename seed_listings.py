from app import app, db
from models import Listing, User
import random

def seed_listings():
    with app.app_context():
        print("🌱 Seeding test listings...")
        
        # Get the first user (usually the admin/first user created)
        user = User.query.first()
        if not user:
            print("❌ No users found! Please register a user first.")
            return

        print(f"👤 Assigning listings to user: {user.email} (ID: {user.id})")

        test_listings = [
            # CYTZ - Billy Bishop Toronto City Airport
            {
                "airport_icao": "CYTZ", 
                "size_sqft": 800, 
                "covered": True, 
                "price_month": 450.0, 
                "description": "Premium covered hangar space tailored for single-engine aircraft. 24/7 security and heated.",
                "condition_verified": True
            },
            {
                "airport_icao": "CYTZ", 
                "size_sqft": 1000, 
                "covered": True, 
                "price_month": 600.0, 
                "description": "Spacious hangar bay, perfect for a Cirrus or similar. Includes access to pilot lounge.",
                "condition_verified": True
            },
            {
                "airport_icao": "CYTZ", 
                "size_sqft": 600, 
                "covered": False, 
                "price_month": 200.0, 
                "description": "Affordable tie-down spot on the north ramp. Easy access.",
                "condition_verified": False
            },

            # KJFK - John F. Kennedy International
            {
                "airport_icao": "KJFK", 
                "size_sqft": 3000, 
                "covered": True, 
                "price_month": 2500.0, 
                "description": "Executive hangar space for light jets. Full FBO services adjacent.",
                "condition_verified": True
            },
            {
                "airport_icao": "KJFK", 
                "size_sqft": 2500, 
                "covered": True, 
                "price_month": 2200.0, 
                "description": "Secure, heated hangar. pristine condition.",
                "condition_verified": True
            },

            # KLAX - Los Angeles International
            {
                "airport_icao": "KLAX", 
                "size_sqft": 2000, 
                "covered": True, 
                "price_month": 1800.0, 
                "description": "Rare opening at KLAX. Private hangar suitable for twin engine.",
                "condition_verified": True
            },

            # CYHM - John C. Munro Hamilton International
            {
                "airport_icao": "CYHM", 
                "size_sqft": 1200, 
                "covered": True, 
                "price_month": 550.0, 
                "description": "Great hangar for GA aircraft. Friendly community.",
                "condition_verified": True
            },
             {
                "airport_icao": "CYHM", 
                "size_sqft": 800, 
                "covered": False, 
                "price_month": 150.0, 
                "description": "Outdoor tie-down. Paved surface.",
                "condition_verified": False
            },
        ]

        count = 0
        for data in test_listings:
            # Check if exists to avoid duplicates
            exists = Listing.query.filter_by(
                airport_icao=data['airport_icao'], 
                price_month=data['price_month'],
                owner_id=user.id
            ).first()

            if not exists:
                listing = Listing(
                    airport_icao=data['airport_icao'],
                    size_sqft=data['size_sqft'],
                    covered=data['covered'],
                    price_month=data['price_month'],
                    description=data['description'],
                    owner_id=user.id,
                    status='Active',
                    condition_verified=data.get('condition_verified', False),
                    likes=random.randint(0, 15) # Add some random likes for the feed
                )
                db.session.add(listing)
                count += 1
        
        db.session.commit()
        print(f"✅ Successfully seeded {count} new listings!")

if __name__ == "__main__":
    seed_listings()

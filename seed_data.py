from app import app, db
from models import User, Listing
from werkzeug.security import generate_password_hash

def seed():
    with app.app_context():
        print("🌱 Seeding data for Price Intelligence check...")
        
        # Create a test owner if not exists
        owner = User.query.filter_by(email='seed_owner@example.com').first()
        if not owner:
            owner = User(
                username='SeedOwner',
                email='seed_owner@example.com',
                password_hash=generate_password_hash('password'),
                role='owner'
            )
            db.session.add(owner)
            db.session.commit()
            print("👤 Created test owner: SeedOwner")
        
        # Create 3 listings at KSEED
        # Ensure listings don't already exist to avoid duplicates if run multiple times
        # Ideally we'd check, but for simplicity I'll just add them. 
        # Actually duplicate listings might skew the test if run multiple times, but that's fine for testing.
        
        listings_data = [
            {'price': 500.0, 'size': 1000, 'covered': False},
            {'price': 700.0, 'size': 1200, 'covered': True},
            {'price': 900.0, 'size': 1500, 'covered': True}
        ]
        
        count = 0
        for data in listings_data:
            # Check if similar listing exists to avoid clutter
            exists = Listing.query.filter_by(
                airport_icao='KSEED', 
                price_month=data['price'],
                owner_id=owner.id
            ).first()
            
            if not exists:
                listing = Listing(
                    airport_icao='KSEED',
                    price_month=data['price'],
                    size_sqft=data['size'],
                    covered=data['covered'],
                    description='Test listing for price intelligence',
                    owner_id=owner.id,
                    status='Active',
                    condition_verified=True
                )
                db.session.add(listing)
                count += 1
        
        db.session.commit()
        print(f"✈️  Added {count} listings at airport 'KSEED'")
        print("✅ Seeding complete!")
        print()
        print("🧪 To Test Price Intelligence:")
        print("   1. Log in (or use existing session)")
        print("   2. Go to: http://localhost:5000/post-listing?airport=KSEED")
        print("   3. Or go to /post-listing and type 'KSEED' in the airport field")
        print("   4. You should see:")
        print("      - Low: $500")
        print("      - Avg: $700")
        print("      - High: $900")

if __name__ == '__main__':
    seed()

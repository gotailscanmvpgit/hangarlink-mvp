import random
from app import create_app
from extensions import db
from models import Listing, User
from config import Config
from datetime import datetime

class DevConfig(Config):
    # Always force local SQLite to ensure stability, bypass Neon DB caching errors entirely
    SQLALCHEMY_DATABASE_URI = 'sqlite:///hangarlink.db'
    
app = create_app(DevConfig)

def seed_load_test():
    with app.app_context():
        print("🌱 Seeding 100 listings for Load Testing...")
        
        # Ensure test user exists
        dummy = User.query.filter_by(email="loadtester@test.com").first()
        if not dummy:
            dummy = User(
                username="LoadTester",
                email="loadtester@test.com",
                password_hash="fake",
                role="owner"
            )
            db.session.add(dummy)
            db.session.commit()
            
        print("Generating heavy bulk listings...")
        
        listings = []
        airports = ['CYTZ', 'KOSH', 'CYHM', 'KLAS', 'KATL']
        
        for i in range(100):
            p_month = random.randint(300, 2000)
            l = Listing(
                airport_icao=random.choice(airports),
                size_sqft=random.randint(400, 5000),
                covered=random.choice([True, False]),
                price_month=p_month,
                price_night=p_month / 30,
                min_stay_nights=random.randint(1, 30),
                description=f"Load Testing Auto-Gen Hangar Space Phase {i}",
                owner_id=dummy.id,
                status="Active",
                health_score=random.randint(50, 100),
                is_featured=random.choice([True, False]),
                created_at=datetime.utcnow()
            )
            listings.append(l)
            
        db.session.bulk_save_objects(listings)
        db.session.commit()
        print("✅ Success! 100 Listings Injected.")

if __name__ == '__main__':
    seed_load_test()

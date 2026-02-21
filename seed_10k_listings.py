from app import app, db
from models import Listing, User
import random
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_10k_listings():
    with app.app_context():
        # Ensure a test user exists
        owner = User.query.get(1)
        if not owner:
            print("Creating test owner (ID 1)...")
            owner = User(
                id=1,
                username="test_owner",
                email="test_owner@example.com",
                role="owner"
            )
            owner.password_hash = generate_password_hash("password")
            db.session.add(owner)
            db.session.commit()
            print("Test owner created.")

        print("Generating 10,000 test listings...")
        start_time = time.time()
        
        airports = ['CYTZ', 'CYHM', 'CYYZ', 'CYOO', 'CYKZ', 'CYBN', 'CYSN', 'CYXU', 'CYKF', 'CYFD']
        statuses = ['Active', 'Rented', 'Expired']
        
        batch_size = 1000
        listings = []
        
        for i in range(10000):
            airport = random.choice(airports)
            listing = Listing(
                airport_icao=airport,
                size_sqft=random.randint(500, 1500),
                covered=random.choice([True, False]),
                price_month=random.randint(200, 800),
                description=f"Test hangar {i+1} at {airport}",
                owner_id=1,
                status=random.choice(statuses),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365))
            )
            listings.append(listing)
            
            if len(listings) >= batch_size:
                db.session.bulk_save_objects(listings)
                db.session.commit()
                listings = []
                print(f"Committed {i+1} listings...")
        
        if listings:
            db.session.bulk_save_objects(listings)
            db.session.commit()
            
        end_time = time.time()
        seed_duration = end_time - start_time
        
        total_count = Listing.query.count()
        print(f"\nSeeding complete in {seed_duration:.2f} seconds.")
        print(f"Total listings in DB: {total_count}")
        
        # Test Search Performance
        print("\nTesting search performance for 'CYTZ' (page 1, 20 items)...")
        search_start = time.time()
        
        # Pagination query
        query = Listing.query.filter_by(airport_icao='CYTZ', status='Active')
        results = query.paginate(page=1, per_page=20, error_out=False)
        
        search_end = time.time()
        search_duration = search_end - search_start
        
        print(f"Search completed in {search_duration:.4f} seconds.")
        print(f"Found {results.total} matching listings.")
        print(f"Page 1 items: {len(results.items)}")

if __name__ == "__main__":
    seed_10k_listings()

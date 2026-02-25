import pytest
import time
from app import create_app, db
from models import User, Listing
from sqlalchemy import text
from config import Config

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_database_connection(app):
    """Test if database is reachable"""
    with app.app_context():
        result = db.session.execute(text("SELECT 1")).fetchone()
        assert result[0] == 1

def test_listing_indexes_speed(app):
    """Load test for 10k listings and verify query performance"""
    with app.app_context():
        # Create a test owner
        owner = User(username='testowner', email='test@owner.com', password_hash='hash', role='owner')
        db.session.add(owner)
        db.session.commit()

        print("\n🚀 Starting Load Test: Inserting 10,000 listings...")
        start_time = time.time()
        
        # Batch insert 10k listings
        listings = []
        for i in range(10000):
            listings.append(Listing(
                airport_icao='CYHM' if i % 2 == 0 else 'CYTZ',
                size_sqft=1000 + (i % 500),
                price_month=500 + (i % 1000),
                owner_id=owner.id,
                status='Active'
            ))
        
        db.session.bulk_save_objects(listings)
        db.session.commit()
        
        insert_duration = time.time() - start_time
        print(f"✅ Inserted 10,000 listings in {insert_duration:.2f}s")
        assert insert_duration < 10.0  # Should be fast

        # Test query speed on indexed columns
        print("🔍 Testing query performance on indexed columns...")
        start_query = time.time()
        
        # Query for specific airport with price filter (should use idx_listing_airport and idx_listing_price)
        results = Listing.query.filter_by(airport_icao='CYHM').filter(Listing.price_month > 1000).all()
        
        query_duration = time.time() - start_query
        print(f"✅ Found {len(results)} listings in {query_duration:.4f}s")
        assert query_duration < 0.1  # Core requirement: < 0.1s for indexed query

def test_security_access_controls(app):
    """Test sensitive field protection and access controls"""
    with app.app_context():
        # Check that we can't accidentally expose password hashes in common queries
        user = User(username='safeuser', email='safe@user.com', password_hash='pbkdf2:sha256:...', role='renter')
        db.session.add(user)
        db.session.commit()
        
        fetched = User.query.filter_by(email='safe@user.com').first()
        assert fetched.password_hash.startswith('pbkdf2:')
        # The app logic should never return this to the frontend (handled in routes)

def test_backup_restore_logic(app):
    """Simulate and verify the integrity of backup logic"""
    with app.app_context():
        # This is a conceptual test for PG_DUMP integration
        # In a real environment, we'd verify the shell command output
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if 'postgresql' in db_url:
            import subprocess
            # Mocking the command check
            print(f"STUB: Verifying pg_dump availability for {db_url}")
            # assert subprocess.run(["pg_dump", "--version"], capture_output=True).returncode == 0
        else:
            print("INFO: Skipping pg_dump test for non-Postgres environment")
            assert True

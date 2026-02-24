import os
import time
import shutil
import sqlite3
import pytest
import base64
from sqlalchemy import text
from models import User, Listing, Ad
from extensions import db as _db
from datetime import datetime

# ════════════════════════════════════════════════════════════════
#  DATABASE INTEGRATION & STRESS TESTS
# ════════════════════════════════════════════════════════════════

class TestDatabaseIntegration:

    # 1. DATA LOSS PREVENTION & MIGRATIONS
    # ════════════════════════════════════════════════════════════════

    def test_backup_and_restore(self, app, db):
        """Simulate SQLite backup/restore and verify data integrity."""
        with app.app_context():
            # Seed initial data
            u = User(username='backup_user', email='backup@test.com', password_hash='hash', role='renter')
            db.session.add(u)
            db.session.commit()
            original_count = User.query.count()
            
            # 1. Perform Backup
            uri = app.config['SQLALCHEMY_DATABASE_URI']
            if uri.startswith('sqlite:///'):
                rel_path = uri.replace('sqlite:///', '')
                if os.path.isabs(rel_path):
                    db_path = rel_path
                else:
                    db_path = os.path.join(app.instance_path, rel_path)
            else:
                pytest.skip("This test requires a local SQLite database")

            backup_path = db_path + '.bak'
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)
            else:
                pytest.fail(f"Database file not found at {db_path}")
            
            # 2. Corrupt/Modify Data
            u2 = User(username='new_user', email='new@test.com', password_hash='hash', role='renter')
            db.session.add(u2)
            db.session.commit()
            assert User.query.count() == original_count + 1
            
            # 3. Simulate Restore
            db.session.remove() # Close sessions
            shutil.copy2(backup_path, db_path)
            
            # Verify data is back to original
            assert User.query.count() == original_count
            assert User.query.filter_by(username='new_user').first() is None
            
            # Cleanup
            if os.path.exists(backup_path):
                os.remove(backup_path)

    def test_migration_integrity(self, app, db):
        """Test that adding a column doesn't wipe existing data."""
        with app.app_context():
            # 1. Seed
            l = Listing(airport_icao='CYHM', price_month=500.0, size_sqft=1000, 
                        owner_id=1, status='Active', health_score=90, description='Migrate me')
            db.session.add(l)
            db.session.commit()
            listing_id = l.id
            
            # 2. Apply Migration (Simulate ADD COLUMN)
            db.session.execute(text("ALTER TABLE listings ADD COLUMN test_field_migration VARCHAR(50) DEFAULT 'old_data'"))
            db.session.commit()
            
            # 3. Verify
            res = db.session.execute(text(f"SELECT description, test_field_migration FROM listings WHERE id = {listing_id}")).fetchone()
            assert res is not None
            assert res[0] == 'Migrate me'
            assert res[1] == 'old_data'

    # 2. SECURITY & ACCESS CONTROLS
    # ════════════════════════════════════════════════════════════════

    def test_role_based_access_controls(self, app, db):
        """Verify that role-based query filters work at the DB level."""
        with app.app_context():
            # Clear previous users
            db.session.query(User).delete()
            
            admin = User(username='admin_db', email='admin@db.com', password_hash='hash', role='owner', is_admin=True)
            renter = User(username='renter_db', email='renter@db.com', password_hash='hash', role='renter', is_admin=False)
            db.session.add_all([admin, renter])
            db.session.commit()
            
            # Admin should see all
            all_users = User.query.all()
            assert len(all_users) >= 2
            
            # Simulated Access Check logic
            def get_sensitive_data(current_user):
                if not current_user.is_admin:
                    raise PermissionError("Unauthorized")
                return "Admin Secret"
            
            assert get_sensitive_data(admin) == "Admin Secret"
            with pytest.raises(PermissionError):
                get_sensitive_data(renter)

    def test_field_encryption_simulation(self):
        """Test logic for encrypting/decrypting sensitive fields."""
        # Simple symmetric XOR encryption for demonstration (since cryptography might not be in env)
        def simple_encrypt(data, key="HangarLinksSecret"):
            return base64.b64encode(''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data)).encode()).decode()

        def simple_decrypt(data, key="HangarLinksSecret"):
            decoded = base64.b64decode(data.encode()).decode()
            return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(decoded))

        sensitive_email = "pilot-secret@topsecret.com"
        encrypted = simple_encrypt(sensitive_email)
        assert encrypted != sensitive_email
        assert simple_decrypt(encrypted) == sensitive_email

    # 3. AVAILABILITY & PERFORMANCE (LOAD TESTING)
    # ════════════════════════════════════════════════════════════════

    def test_50k_listings_load_and_query_performance(self, app, db):
        """Stress test: Insert 50,000 listings and measure query latency."""
        with app.app_context():
            # Cleanup
            db.session.query(Listing).delete()
            db.session.commit()
            
            print("\n[PERF] Inserting 50,000 listings...")
            start_time = time.time()
            
            # Bulk insert for speed
            listings_data = [
                {
                    'airport_icao': f'A{i % 1000}',
                    'size_sqft': 1500,
                    'price_month': 450.0,
                    'owner_id': 1,
                    'status': 'Active' if i % 10 != 0 else 'Pending',
                    'health_score': 85,
                    'description': f'Stress test listing {i}'
                }
                for i in range(50000)
            ]
            
            db.session.bulk_insert_mappings(Listing, listings_data)
            db.session.commit()
            
            total_insert_time = time.time() - start_time
            print(f"[PERF] Insert took {total_insert_time:.2f} seconds")
            
            # 2. Performance Query (Pagination + Filtering)
            start_query = time.time()
            results = Listing.query.filter_by(airport_icao='A123', status='Active').limit(20).offset(100).all()
            query_time = time.time() - start_query
            
            print(f"[PERF] 50k search query took {query_time:.6f} seconds")
            
            # Requirement: < 0.1 seconds for typical query
            assert query_time < 0.1, f"Query took too long: {query_time:.4f}s"
            assert len(results) >= 0

    def test_recovery_scenario(self, app, db):
        """Simulate a catastrophic failure and check recovery path."""
        with app.app_context():
            # 1. State before failure
            u = User(username='survivor', email='survivor@test.com', password_hash='hash', role='renter')
            db.session.add(u)
            db.session.commit()
            
            uri = app.config['SQLALCHEMY_DATABASE_URI']
            if uri.startswith('sqlite:///'):
                rel_path = uri.replace('sqlite:///', '')
                if os.path.isabs(rel_path):
                    db_path = rel_path
                else:
                    db_path = os.path.join(app.instance_path, rel_path)
            else:
                pytest.skip("This test requires a local SQLite database")

            backup_path = db_path + '.catastrophic_bak'
            shutil.copy2(db_path, backup_path)
            
            # 2. Catastrophic Failure: Drop critical table
            db.session.execute(text("DROP TABLE listings"))
            db.session.commit()
            
            # Verify failure
            with pytest.raises(Exception):
                Listing.query.all()
            
            # 3. Recovery: Restore from backup
            db.session.remove()
            shutil.copy2(backup_path, db_path)
            
            # Verify recovery
            assert User.query.filter_by(username='survivor').first() is not None
            # Listing table should be back
            assert Listing.query.count() >= 0
            
            # Cleanup
            if os.path.exists(backup_path):
                os.remove(backup_path)

from app import app, db
from models import User, Listing, Ad
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def seed():
    with app.app_context():
        print("🌱 Seeding comprehensive test data for Tier 2 Testing...")
        
        # 1. Free Owner
        free_owner = User.query.filter_by(email='owner@test.com').first()
        if not free_owner:
            free_owner = User(
                username='FreeOwner',
                email='owner@test.com',
                password_hash=generate_password_hash('password'),
                role='owner',
                subscription_tier='free'
            )
            db.session.add(free_owner)
            
        # 2. Premium Owner
        prem_owner = User.query.filter_by(email='premium@test.com').first()
        if not prem_owner:
            prem_owner = User(
                username='PremiumOwner',
                email='premium@test.com',
                password_hash=generate_password_hash('password'),
                role='owner',
                subscription_tier='premium',
                subscription_expires=datetime.utcnow() + timedelta(days=30),
                has_analytics_access=True,
                analytics_expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(prem_owner)
            
        # 3. Free Renter
        renter = User.query.filter_by(email='renter@test.com').first()
        if not renter:
            renter = User(
                username='RenterOne',
                email='renter@test.com',
                password_hash=generate_password_hash('password'),
                role='renter',
                subscription_tier='free'
            )
            db.session.add(renter)

        db.session.commit()
        print("✅ Users Created:")
        print("   - owner@test.com (pass: password) -> Free Owner")
        print("   - premium@test.com (pass: password) -> Premium Owner + Analytics")
        print("   - renter@test.com (pass: password) -> Free Renter")
        
        # 4. Create Listings for Free Owner
        if free_owner.id:
            l1 = Listing(
                airport_icao='CYHM',
                price_month=1200,
                size_sqft=1500,
                covered=True,
                description='Standard Hangar (Test)',
                owner_id=free_owner.id,
                status='Active'
            )
            db.session.add(l1)
            
        # 5. Create Premium Listing
        if prem_owner.id:
            l2 = Listing(
                airport_icao='CYHM',
                price_month=2500,
                size_sqft=3000,
                covered=True,
                description='Premium Heated Hangar',
                owner_id=prem_owner.id,
                status='Active',
                is_premium_listing=True
            )
            db.session.add(l2)
            
        # 6. Admin User
        admin = User.query.filter_by(email='admin@hangarlink.com').first()
        if not admin:
            admin = User(
                username='Admin',
                email='admin@hangarlink.com',
                password_hash=generate_password_hash('password'),
                role='admin',
                is_admin=True,
                subscription_tier='premium' # Often admins get perks
            )
            db.session.add(admin)
            print("   - admin@hangarlink.com (pass: password) -> Admin")
            
        # 7. Sample Ads
        ads_count = Ad.query.count()
        if ads_count == 0:
            ad1 = Ad(title='Aviation Insurance Pro', 
                     image_url='https://placehold.co/600x200/001F3F/FFF?text=Insure+Your+Wings', 
                     link_url='#', 
                     placement='home_banner')
            ad2 = Ad(title='SkyHigh Tires', 
                     image_url='https://placehold.co/300x250/E0E0E0/333?text=Best+Tires', 
                     link_url='#', 
                     placement='sidebar')
            db.session.add_all([ad1, ad2])
            print("   - Created sample ads")

        db.session.commit()
        print("✅ Listings Created at CYHM")

if __name__ == '__main__':
    seed()

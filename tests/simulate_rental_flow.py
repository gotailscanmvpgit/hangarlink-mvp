import sys
import os
from datetime import datetime, timedelta
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import User, Listing, Booking, Payment

def simulate():
    with app.app_context():
        # 1. Create Users
        owner = User.query.filter_by(email='owner55@yahoo.com').first()
        if not owner:
            owner = User(username='owner55', email='owner55@yahoo.com', role='owner', first_name='John', last_name='Lessor')
            owner.password_hash = 'pbkdf2:sha256:...' # simplified
            db.session.add(owner)
        
        renter = User.query.filter_by(email='pilot55@yahoo.com').first()
        if not renter:
            renter = User(username='pilot55', email='pilot55@yahoo.com', role='renter', first_name='Jane', last_name='Lessee')
            renter.password_hash = 'pbkdf2:sha256:...' # simplified
            db.session.add(renter)
        
        db.session.commit()
        
        # 2. Create Listing
        listing = Listing.query.filter_by(owner_id=owner.id, airport_icao='KIAH').first()
        if not listing:
            listing = Listing(
                owner_id=owner.id,
                airport_icao='KIAH',
                size_sqft=2000,
                price_month=800.0,
                price_night=80.0,
                status='Active'
            )
            db.session.add(listing)
            db.session.commit()

        # 3. Create Booking (Simulate successful checkout)
        session_id = "test_stripe_session_123"
        booking = Booking(
            listing_id=listing.id,
            renter_id=renter.id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            total_price=560.0,
            status='Pending',
            stripe_payment_id=session_id
        )
        db.session.add(booking)
        
        payment = Payment(
            user_id=renter.id,
            amount=560.0,
            item_type='rental_booking',
            item_id=listing.id,
            stripe_session_id=session_id,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        print(f"--- SIMULATION START ---")
        print(f"Booking ID: {booking.id}")
        
        # 4. Trigger the logic from booking_success
        platform_fee_rate = 0.10
        owner_share = 1.0 - platform_fee_rate
        revenue = booking.total_price * owner_share
        
        booking.status = 'Confirmed'
        listing.status = 'Rented'
        
        if owner.total_revenue is None: owner.total_revenue = 0.0
        owner.total_revenue += revenue
        payment.status = 'completed'
        
        db.session.commit()
        
        print(f"Status Updated: {booking.status}")
        print(f"Owner Revenue Added: ${revenue:.2f}")
        print(f"Total Owner Earnings: ${owner.total_revenue:.2f}")
        print(f"--- SIMULATION END ---")

if __name__ == "__main__":
    simulate()

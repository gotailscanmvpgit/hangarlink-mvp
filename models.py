from extensions import db
from flask_login import UserMixin
from datetime import datetime
from flask_caching import Cache

# ... User model omitted ... 

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'owner' or 'renter'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Alert Preferences (for Smart Availability Alerts)
    alert_enabled = db.Column(db.Boolean, default=False)
    alert_airport = db.Column(db.String(4), nullable=True)
    alert_max_price = db.Column(db.Float, nullable=True)
    alert_min_size = db.Column(db.Integer, nullable=True)
    alert_covered_only = db.Column(db.Boolean, default=False)
    
    # Relationships
    listings = db.relationship('Listing', backref='owner', lazy=True)
    
    # New Features
    reputation_score = db.Column(db.Float, default=5.0)
    rentals_count = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
    
    # Subscription & Monetization
    subscription_tier = db.Column(db.String(20), default='free')  # 'free', 'premium'
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_expires = db.Column(db.DateTime, nullable=True)
    
    # Analytics & Insights (Tier 2)
    has_analytics_access = db.Column(db.Boolean, default=False)
    analytics_expires_at = db.Column(db.DateTime, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    search_count_today = db.Column(db.Integer, default=0)


    search_reset_date = db.Column(db.Date, nullable=True)
    
    # Feature 5 & 6: Rewards & Referrals
    points = db.Column(db.Integer, default=0)
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Feature 7: Certified Owner
    is_certified = db.Column(db.Boolean, default=False)
    seasonal_alerts = db.Column(db.Boolean, default=True) # Feature 4
    
    def __repr__(self):
        return f'<User {self.email}>'

class Listing(db.Model):
    __tablename__ = 'listings'
    
    # Add indexes for scalability
    __table_args__ = (
        db.Index('idx_listing_airport', 'airport_icao'),
        db.Index('idx_listing_price', 'price_month'),
        db.Index('idx_listing_status', 'status'),
        db.Index('idx_listing_created', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    airport_icao = db.Column(db.String(4), nullable=False)
    size_sqft = db.Column(db.Integer, nullable=False)
    covered = db.Column(db.Boolean, default=False)
    price_month = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    photos = db.Column(db.Text, nullable=True)  # Comma-separated filenames
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Active')  # 'Active', 'Inactive', 'Rented'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Monetization Tier 2
    is_featured = db.Column(db.Boolean, default=False)
    featured_expires_at = db.Column(db.DateTime, nullable=True)
    featured_tier = db.Column(db.String(20), nullable=True) # 'silver', 'gold', 'platinum'
    insurance_active = db.Column(db.Boolean, default=False) # Owner purchased/verified insurance
    
    # New Features
    condition_verified = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    video_url = db.Column(db.String(255), nullable=True) # For verified hangar program
    virtual_tour_url = db.Column(db.String(255), nullable=True) # Feature 2: 360/Video Tour
    # insurance_active was here, moving up to group with monetization
    health_score = db.Column(db.Integer, default=0)
    checklist_completed = db.Column(db.Boolean, default=False)
    availability_start = db.Column(db.Date, nullable=True)
    availability_end = db.Column(db.Date, nullable=True)
    is_premium_listing = db.Column(db.Boolean, default=False)  # Premium listings get priority
    
    # Relationships
    bookings = db.relationship('Booking', backref='listing', lazy=True)

    def get_price_intelligence(self):
        """Get average price range for similar listings at this airport"""
        similar_listings = Listing.query.filter(
            Listing.airport_icao == self.airport_icao,
            Listing.status == 'Active',
            Listing.id != self.id 
        ).all()
        
        if not similar_listings:
            return None
            
        prices = [l.price_month for l in similar_listings]
        return {
            'min': min(prices),
            'max': max(prices),
            'avg': sum(prices) / len(prices),
            'count': len(prices)
        }

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    renter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Confirmed, Cancelled, Completed
    stripe_payment_id = db.Column(db.String(100), nullable=True)
    
    # Tiert 2: Insurance Add-on
    insurance_opt_in = db.Column(db.Boolean, default=False)
    insurance_fee = db.Column(db.Float, default=0.0)
    
    # Reviews
    owner_rating = db.Column(db.Integer, nullable=True)
    renter_rating = db.Column(db.Integer, nullable=True)
    owner_review = db.Column(db.Text, nullable=True)
    renter_review = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to renter
    renter = db.relationship('User', backref='bookings')

    def __repr__(self):
        return f'<Booking {self.id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Nullable for guest
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    is_guest = db.Column(db.Boolean, default=False)
    guest_email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    listing = db.relationship('Listing', backref='messages')
    
    
    def __repr__(self):
        return f'<Message from {self.sender_id} to {self.receiver_id}>'

class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    link_url = db.Column(db.String(500), nullable=False)
    placement = db.Column(db.String(50))
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Valid model now ends at created_at above.
    def __repr__(self):
        return f'<Ad {self.title}>'


class WhiteLabelRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fbo_name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Optimization Indexes
db.Index('idx_airport', Listing.airport_icao)
db.Index('idx_price', Listing.price_month)
db.Index('idx_status', Listing.status)
db.Index('idx_created', Listing.created_at)
db.Index('idx_owner', Listing.owner_id)
db.Index('idx_covered', Listing.covered)
db.Index('idx_featured', Listing.is_featured)
db.Index('idx_premium_listing', Listing.is_premium_listing)

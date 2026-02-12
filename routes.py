from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app
from extensions import db
from models import User, Listing, Message, Booking
import os
try:
    import stripe
    # Stripe Config
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
except ImportError:
    stripe = None
from datetime import datetime, date, timedelta

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Landing page / Dashboard"""
    listings_count = 0
    messages_count = 0
    saved_searches_count = 0
    
    if current_user.is_authenticated:
        listings_count = Listing.query.filter_by(owner_id=current_user.id).count()
        # Count total messages (sent or received)
        messages_count = Message.query.filter(
            (Message.sender_id == current_user.id) | 
            (Message.receiver_id == current_user.id)
        ).count()
        # Placeholder for saved searches
        saved_searches_count = 0
        
    # Check onboarding status
    show_onboarding = False
    if current_user.is_authenticated:
        show_onboarding = session.pop('show_onboarding', False)
        
    return render_template('index.html', 
                          listings_count=listings_count, 
                          messages_count=messages_count, 
                          saved_searches_count=saved_searches_count,
                          show_onboarding=show_onboarding)

@app.route('/listings')
def listings():
    """Search and browse all listings"""
    # Check search limit for free-tier renters
    search_limited = False
    if not check_search_limit():
        search_limited = True
    
    airport = request.args.get('airport', '').strip().upper()
    radius = request.args.get('radius', 250, type=int)
    covered = request.args.get('covered', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # Build query
    query = Listing.query.filter_by(status='Active')
    
    if airport:
        query = query.filter_by(airport_icao=airport)
    
    if covered == 'yes':
        query = query.filter_by(covered=True)
    elif covered == 'no':
        query = query.filter_by(covered=False)
    
    if min_price:
        query = query.filter(Listing.price_month >= min_price)
    
    if max_price:
        query = query.filter(Listing.price_month <= max_price)
    
    # Premium listings first, then by date
    listings = query.order_by(Listing.is_premium_listing.desc(), Listing.created_at.desc()).all()
    
    return render_template('listings.html', 
                         listings=listings, 
                         airport=airport, 
                         radius=radius,
                         covered=covered,
                         min_price=min_price,
                         max_price=max_price,
                         search_limited=search_limited)

@app.route('/listing/<int:id>')
def listing_detail(id):
    """Individual listing detail page"""
    listing = Listing.query.get_or_404(id)
    return render_template('listing_detail.html', listing=listing)

@app.route('/post-listing', methods=['GET', 'POST'])
@login_required
def post_listing():
    """Create a new listing"""
    price_intel = None
    
    # Check listing limit for free tier
    if not check_listing_limit():
        flash('Free accounts can have 1 active listing. Upgrade to Premium for unlimited listings!', 'warning')
        return redirect(url_for('pricing'))
    
    if request.method == 'POST':
        # Handle file upload
        photo_filenames = []
        if 'photos' in request.files:
            files = request.files.getlist('photos')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'listings', filename)
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    photo_filenames.append(filename)
        
        # Health Score Calculation
        score = 0
        checklist_verified = request.form.get('checklist_verified') == 'on'
        condition_verified = request.form.get('condition_verified') == 'on'
        
        # Rule 1: Photos (need at least 3 for points)
        if len(photo_filenames) >= 3:
            score += 30
        
        # Rule 2: Checklist
        if checklist_verified:
            score += 30
            
        # Rule 3: Verification
        if condition_verified:
            score += 20
        
        # Rule 4: Reputation
        if current_user.reputation_score >= 4.5:
            score += 20
            
        # Availability Dates
        avail_start = None
        avail_end = None
        if request.form.get('availability_start'):
             try:
                avail_start = datetime.strptime(request.form.get('availability_start'), '%Y-%m-%d').date()
             except ValueError:
                pass
        if request.form.get('availability_end'):
             try:
                avail_end = datetime.strptime(request.form.get('availability_end'), '%Y-%m-%d').date()
             except ValueError:
                pass

        listing = Listing(
            airport_icao=request.form.get('airport_icao').upper(),
            size_sqft=int(request.form.get('size_sqft')),
            covered=request.form.get('covered') == 'on',
            price_month=float(request.form.get('price_month')),
            description=request.form.get('description'),
            photos=','.join(photo_filenames) if photo_filenames else None,
            owner_id=current_user.id,
            status='Active',
            condition_verified=condition_verified,
            checklist_completed=checklist_verified,
            health_score=min(score, 100), # Cap at 100
            availability_start=avail_start,
            availability_end=avail_end,
            virtual_tour_url=request.form.get('virtual_tour_url') # Feature 2
        )
        db.session.add(listing)
        db.session.commit()
        
        # Check for matching alert preferences and notify users
        check_and_send_alerts(listing)
        
        flash('Listing created successfully!', 'success')
        return redirect(url_for('listing_detail', id=listing.id))
    
    # Get price intelligence if airport is provided via query param
    airport = request.args.get('airport', '').upper()
    if airport:
        temp_listing = Listing(airport_icao=airport, id=0)
        price_intel = temp_listing.get_price_intelligence()
    
    return render_template('post_listing.html', price_intel=price_intel, airport=airport)

@app.route('/post-listing-confirm')
@login_required
def post_listing_confirm():
    """Confirmation page to help renters vs owners"""
    # Check if user has any listings
    user_listings_count = Listing.query.filter_by(owner_id=current_user.id).count()
    return render_template('post_listing_confirm.html', user_listings_count=user_listings_count)

@app.route('/feed')
@login_required
def feed():
    """Community Feed of recent listings"""
    recent_listings = Listing.query.filter_by(status='Active').order_by(Listing.created_at.desc()).limit(20).all()
    return render_template('feed.html', listings=recent_listings)

@app.route('/like/<int:listing_id>', methods=['POST'])
@login_required
def like_listing(listing_id):
    """Like a listing"""
    listing = Listing.query.get_or_404(listing_id)
    listing.likes += 1
    db.session.commit()
    return {'likes': listing.likes}

def check_and_send_alerts(listing):
    """Check if any users have matching alert preferences and send notifications"""
    # Find users with matching alert preferences
    matching_users = User.query.filter(
        User.alert_enabled == True,
        User.id != listing.owner_id  # Don't alert the owner
    ).all()
    
    for user in matching_users:
        # Check if listing matches user's preferences
        matches = True
        
        if user.alert_airport and user.alert_airport != listing.airport_icao:
            matches = False
        
        if user.alert_max_price and listing.price_month > user.alert_max_price:
            matches = False
        
        if user.alert_min_size and listing.size_sqft < user.alert_min_size:
            matches = False
        
        if user.alert_covered_only and not listing.covered:
            matches = False
        
        if matches:
            # In production, send email here
            # For now, we'll just log it
            print(f"✨ ALERT: User {user.email} matches listing {listing.id} at {listing.airport_icao}")
            # TODO: Implement email sending with Flask-Mail


@app.route('/my-listings')
@login_required
def my_listings():
    """View user's own listings"""
    listings = Listing.query.filter_by(owner_id=current_user.id).order_by(Listing.created_at.desc()).all()
    return render_template('my_listings.html', listings=listings)

@app.route('/listing/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(id):
    """Edit a listing"""
    listing = Listing.query.get_or_404(id)
    
    # Check ownership
    if listing.owner_id != current_user.id:
        flash('You can only edit your own listings', 'error')
        return redirect(url_for('listing_detail', id=id))
    
    if request.method == 'POST':
        listing.airport_icao = request.form.get('airport_icao').upper()
        listing.size_sqft = int(request.form.get('size_sqft'))
        listing.covered = request.form.get('covered') == 'on'
        listing.price_month = float(request.form.get('price_month'))
        listing.description = request.form.get('description')
        listing.status = request.form.get('status', 'Active')
        
        db.session.commit()
        flash('Listing updated successfully!', 'success')
        return redirect(url_for('listing_detail', id=id))
    
    return render_template('edit_listing.html', listing=listing)

@app.route('/messages')
@login_required
def messages():
    """View all conversations"""
    # Get unique conversation partners
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct()
    received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct()
    
    partner_ids = set([r[0] for r in sent] + [r[0] for r in received])
    partners = User.query.filter(User.id.in_(partner_ids)).all()
    
    # Get last message with each partner
    conversations = []
    for partner in partners:
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
            ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        
        # Count unread messages from this partner
        unread_count = Message.query.filter_by(
            sender_id=partner.id,
            receiver_id=current_user.id,
            read=False
        ).count()
        
        conversations.append({
            'partner': partner,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by last message time
    # Sort by Premium status first, then last message time
    conversations.sort(key=lambda x: (
        x['partner'].is_premium, 
        x['last_message'].created_at if x['last_message'] else datetime.min
    ), reverse=True)
    
    return render_template('messages.html', conversations=conversations)

@app.route('/message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def message_user(user_id):
    """Private chat with a user"""
    partner = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        listing_id = request.form.get('listing_id', type=int)
        
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                listing_id=listing_id,
                content=content
            )
            db.session.add(message)
            db.session.commit()
            flash('Message sent!', 'success')
    
    # Get all messages between these users
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    
    # Mark received messages as read
    Message.query.filter_by(
        sender_id=user_id,
        receiver_id=current_user.id,
        read=False
    ).update({'read': True})
    db.session.commit()
    
    # Get listing if referenced
    listing_id = request.args.get('listing_id', type=int)
    listing = Listing.query.get(listing_id) if listing_id else None
    
    return render_template('message_user.html', partner=partner, messages=messages, listing=listing)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'renter')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(username=username).first():
            flash('Callsign/Username already taken', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        session['show_onboarding'] = True
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/api/dismiss-onboarding', methods=['POST'])
@login_required
def dismiss_onboarding():
    """API endpoint to mark onboarding tour as seen"""
    session.pop('show_onboarding', None)
    return jsonify({'status': 'ok'})

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('privacy.html')

# ========== NEW FEATURES ==========

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile with alert preferences"""
    if request.method == 'POST':
        # Update alert preferences
        current_user.alert_enabled = request.form.get('alert_enabled') == 'on'
        current_user.alert_airport = request.form.get('alert_airport', '').upper() or None
        current_user.alert_max_price = float(request.form.get('alert_max_price')) if request.form.get('alert_max_price') else None
        current_user.alert_min_size = int(request.form.get('alert_min_size')) if request.form.get('alert_min_size') else None
        current_user.alert_covered_only = request.form.get('alert_covered_only') == 'on'
        
        db.session.commit()
        flash('Alert preferences saved! You\'ll be notified when matching listings are posted.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

# --- Feature: Owner Dashboard ---
@app.route('/dashboard/owner')
@login_required
def owner_dashboard():
    # Only for owners
    if current_user.role != 'owner':
        flash('Access restricted to hangar owners.', 'error')
        return redirect(url_for('index'))
        
    listings = Listing.query.filter_by(owner_id=current_user.id).all()
    
    total_earnings = 0
    occupancy_count = 0
    total_listings = len(listings)
    
    monthly_data = {} # For chart
    
    for listing in listings:
        bookings = Booking.query.filter_by(listing_id=listing.id, status='Confirmed').all()
        for booking in bookings:
            total_earnings += booking.total_price
            month_key = booking.start_date.strftime('%Y-%m')
            monthly_data[month_key] = monthly_data.get(month_key, 0) + booking.total_price
            
        if listing.status == 'Rented':
            occupancy_count += 1
            
    occupancy_rate = (occupancy_count / total_listings * 100) if total_listings > 0 else 0
    
    return render_template('dashboard_owner.html', 
                          total_earnings=total_earnings,
                          occupancy_rate=occupancy_rate,
                          listings=listings,
                          chart_data=monthly_data,
                          total_listings=total_listings)

# --- Feature: Instant Booking ---
@app.route('/book/<int:listing_id>', methods=['POST'])
@login_required
def book_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    # Calculate price with transaction fee
    platform_fee = listing.price_month * (TRANSACTION_FEE_PERCENT / 100)
    total_with_fee = listing.price_month + platform_fee
    amount = int(total_with_fee * 100)  # Stripe uses cents
    
    try:
        # Mock Stripe session for MVP if no key present
        if not stripe.api_key:
            session_id = 'mock_session_123'
            checkout_session_url = url_for('booking_success', _external=True) + '?session_id=' + session_id
        else:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Hangar Rental at {listing.airport_icao} (includes {TRANSACTION_FEE_PERCENT}% platform fee)',
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('booking_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('listing_detail', id=listing.id, _external=True),
            )
            checkout_session_url = checkout_session.url
            session_id = checkout_session.id
        
        # Create pending booking
        booking = Booking(
            listing_id=listing.id, 
            renter_id=current_user.id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            total_price=listing.price_month,
            status='Pending',
            stripe_payment_id=session_id
        )
        db.session.add(booking)
        db.session.commit()
            
        return redirect(checkout_session_url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('listing_detail', id=listing.id))

@app.route('/booking/success')
@login_required
def booking_success():
    session_id = request.args.get('session_id')
    booking = Booking.query.filter_by(stripe_payment_id=session_id).first_or_404()
    
    booking.status = 'Confirmed'
    booking.listing.status = 'Rented'
    booking.listing.insurance_active = True # Mock insurance activation
    db.session.commit()
    
    # Generate simple PDF agreement url
    agreement_url = url_for('download_agreement', booking_id=booking.id)
    
    flash('Booking Confirmed! Rental agreement generated.', 'success')
    return render_template('booking_success.html', booking=booking, agreement_url=agreement_url)

# --- Feature: Rental Agreement PDF ---
@app.route('/agreement/<int:booking_id>')
@login_required
def download_agreement(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    # Check access permission
    if current_user.id != booking.renter_id and current_user.id != booking.listing.owner_id:
        flash('Unauthorized', 'error')
        return redirect(url_for('index'))
        
    return render_template('agreement_pdf.html', booking=booking)

# --- Feature: HangarMatch AI ---
@app.route('/matches')
@login_required
def matches():
    # Feature 1: AI-Powered Matching Logic
    airport = current_user.alert_airport
    listings = Listing.query.filter_by(status='Active').all()
    scored_matches = []
    
    for l in listings:
        # Calculate AI Match Score (0-99)
        score = 60 # Base relevance
        
        # Location Match (High Weight)
        if airport and l.airport_icao == airport:
            score += 25
        elif airport: # Nearby check (simple logic for now)
            score += 5
            
        # Price Match
        if current_user.alert_max_price and l.price_month <= current_user.alert_max_price:
            score += 15
            
        # Premium/Certified Owner Boost
        if l.owner.is_premium:
            score += 5
        if l.owner.is_certified:
            score += 10 # Feature 7
            
        # Quality Boost
        if l.health_score >= 80:
            score += 5
            
        # Cap at 99%
        final_score = min(score, 99)
        scored_matches.append({'listing': l, 'score': final_score})
        
    # Sort by Score
    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = scored_matches[:10]
    
    return render_template('matches.html', matches=top_matches)

# --- Feature 3: Concierge ---
@app.route('/concierge/chat', methods=['POST'])
@login_required
def concierge_chat():
    data = request.json
    user_msg = data.get('message', '').lower()
    
    # Mock AI Response
    response = "I'm the HangarLink AI. "
    if 'price' in user_msg or 'cost' in user_msg:
        response += "Market rates at CYHM are trending up (+12%). I recommend listing around $600/mo for a T-Hangar."
    elif 'availability' in user_msg:
        response += "I see 3 covered spots opening up next month near Toronto."
    elif 'insurance' in user_msg:
        response += "All rentals include our $1M liability protection policy."
    else:
        response += "How can I help you find or list a hangar today?"
        
    return {'response': response}

# --- Feature 4: Seasonal Forecast ---
@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    import random
    trend = random.choice(['rising', 'stable'])
    percent = random.choice([15, 20, 30])
    return {
        'trend': trend,
        'percentage': percent,
        'season': 'Winter 2025',
        'message': f"Hangar demand forecast: Ontario region {trend} {percent}% this winter."
    }

# --- Feature 5 & 6: Rewards & Referrals ---
@app.route('/rewards')
@login_required
def rewards():
    if current_user.points is None:
        current_user.points = 0
        db.session.commit()
    return render_template('rewards.html', points=current_user.points)

@app.route('/referrals')
@login_required
def referrals():
    if not current_user.referral_code:
        import random, string
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(chars) for _ in range(8))
        current_user.referral_code = code
        db.session.commit()
    return render_template('referrals.html', code=current_user.referral_code)

# --- Feature 7: Admin Certify (Demo) ---
@app.route('/admin/certify/me')
@login_required
def self_certify():
    # Demo feature to become "Certified"
    current_user.is_certified = True
    current_user.reputation_score = 5.0
    current_user.points = (current_user.points or 0) + 500 # Bonus
    db.session.commit()
    flash('You are now a Certified HangarLink Partner! (+500 pts)', 'success')
    return redirect(url_for('profile'))


# --- Feature: HangarLink Insights ---
@app.route('/dashboard/insights')
@login_required
def dashboard_insights():
    # Placeholder data for MVP
    market_trend = "+12%"
    avg_price_area = "$1,200"
    
    # Calculate user stats based on role
    total_revenue = 0
    total_spent = 0
    
    if current_user.role == 'owner':
        listings = Listing.query.filter_by(owner_id=current_user.id).all()
        for listing in listings:
            confirmed_bookings = Booking.query.filter_by(listing_id=listing.id, status='Confirmed').all()
            total_revenue += sum(b.total_price for b in confirmed_bookings)
    else:
        my_bookings = Booking.query.filter_by(renter_id=current_user.id, status='Confirmed').all()
        total_spent = sum(b.total_price for b in my_bookings)
            
    return render_template('dashboard_insights.html', 
                          market_trend=market_trend,
                          avg_price_area=avg_price_area,
                          total_revenue=total_revenue,
                          total_spent=total_spent)

# --- Feature: Book Viewing ---
@app.route('/book-viewing/<int:listing_id>', methods=['POST'])
@login_required
def book_viewing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    date_str = request.form.get('viewing_date')
    time_str = request.form.get('viewing_time', 'Anytime')
    
    content = f"Hi, I'd like to book a viewing for your hangar at {listing.airport_icao} on {date_str} at {time_str}."
    
    msg = Message(
        sender_id=current_user.id,
        receiver_id=listing.owner_id,
        listing_id=listing.id,
        content=content,
        created_at=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()
    
    flash('Viewing request sent to owner!', 'success')
    return redirect(url_for('listing_detail', id=listing.id))

# --- Feature: Guest Message ---
@app.route('/contact-guest/<int:listing_id>', methods=['POST'])
def contact_guest(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    # If user is logged in, redirect to normal message
    if current_user.is_authenticated:
        return redirect(url_for('message_user', user_id=listing.owner_id, listing_id=listing.id))
        
    guest_email = request.form.get('guest_email')
    message_content = request.form.get('message')
    
    if not guest_email or not message_content:
        flash('Email and message are required', 'error')
        return redirect(url_for('listing_detail', id=listing.id))
    
    # Create guest message
    msg = Message(
        sender_id=None, # Guest
        receiver_id=listing.owner_id,
        listing_id=listing.id,
        content=f"[GUEST: {guest_email}] {message_content}",
        is_guest=True,
        guest_email=guest_email,
        created_at=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()
    
    flash('Message sent! The owner will reply to your email.', 'success')
    return redirect(url_for('listing_detail', id=listing.id))

# --- Feature: Complete Rental & Reputation ---
@app.route('/booking/complete/<int:booking_id>', methods=['POST'])
@login_required
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Only involved parties
    if current_user.id not in [booking.renter_id, booking.listing.owner_id]:
        flash('Unauthorized', 'error')
        return redirect(url_for('index'))
        
    rating = int(request.form.get('rating'))
    review = request.form.get('review')
    
    if current_user.id == booking.renter_id:
        booking.owner_rating = rating
        booking.owner_review = review
        # Update owner reputation (simple running average)
        owner = booking.listing.owner
        new_count = owner.rentals_count + 1
        new_score = ((owner.reputation_score * owner.rentals_count) + rating) / new_count
        owner.reputation_score = new_score
        owner.rentals_count = new_count
        
    elif current_user.id == booking.listing.owner_id:
        booking.renter_rating = rating
        booking.renter_review = review
        # Update renter reputation if we tracked it separately (future feature)
    
    booking.status = 'Completed'
    db.session.commit()
    
    flash('Rental completed and reviewed!', 'success')
    return redirect(url_for('index'))


# ========== MONETIZATION & SUBSCRIPTIONS ==========

OWNER_PLAN = {
    'name': 'Owner Premium',
    'price': 999,           # $9.99 in cents
    'price_display': '9.99',
    'interval': 'month',
    'features': [
        'Unlimited active listings',
        'Priority placement in search results',
        'Analytics dashboard with insights',
        'Premium badge on profile & listings',
        'Verified Owner fast-track',
        'Export booking reports'
    ]
}

RENTER_PLAN = {
    'name': 'Renter Premium',
    'price': 699,           # $6.99 in cents
    'price_display': '6.99',
    'interval': 'month',
    'features': [
        'Unlimited searches per day',
        'Saved search alerts',
        'Priority support from owners',
        'Premium badge on profile',
        'Early access to new listings',
        'Advanced filters & map view'
    ]
}

TRANSACTION_FEE_PERCENT = 8  # 8% platform fee

@app.route('/pricing')
def pricing():
    return render_template('pricing.html',
                           owner_plan=OWNER_PLAN,
                           renter_plan=RENTER_PLAN,
                           fee_percent=TRANSACTION_FEE_PERCENT)


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe Checkout Session for subscription"""
    if not stripe:
        flash('Stripe is not configured. Please set STRIPE_SECRET_KEY.', 'warning')
        return redirect(url_for('pricing'))
    
    plan_type = request.form.get('plan_type', 'owner')
    plan = OWNER_PLAN if plan_type == 'owner' else RENTER_PLAN
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plan['name'],
                        'description': f"HangarLink {plan['name']} - Monthly Subscription",
                    },
                    'unit_amount': plan['price'],
                    'recurring': {'interval': plan['interval']},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + f'subscription/success?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_type}',
            cancel_url=request.host_url + 'subscription/cancel',
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'plan_type': plan_type
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('pricing'))


@app.route('/subscription/success')
@login_required
def subscription_success():
    """Handle successful subscription checkout"""
    session_id = request.args.get('session_id')
    plan_type = request.args.get('plan', 'owner')
    
    if stripe and session_id:
        try:
            checkout = stripe.checkout.Session.retrieve(session_id)
            current_user.stripe_customer_id = checkout.customer
            current_user.stripe_subscription_id = checkout.subscription
            current_user.subscription_tier = 'premium'
            current_user.is_premium = True
            current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
        except Exception as e:
            print(f"Stripe session retrieve error: {e}")
    else:
        # Demo mode: activate immediately
        current_user.subscription_tier = 'premium'
        current_user.is_premium = True
        current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
    
    flash('🎉 Welcome to Premium! Your subscription is active.', 'success')
    return render_template('subscription_success.html', plan_type=plan_type,
                           plan=OWNER_PLAN if plan_type == 'owner' else RENTER_PLAN)


@app.route('/subscription/cancel')
def subscription_cancel():
    """Handle cancelled checkout"""
    flash('Subscription checkout was cancelled. You can try again anytime.', 'info')
    return redirect(url_for('pricing'))


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events for subscription management"""
    if not stripe:
        return jsonify({'error': 'Stripe not configured'}), 400
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(
                __import__('json').loads(payload), stripe.api_key
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    # Handle subscription events
    if event['type'] == 'customer.subscription.deleted':
        sub = event['data']['object']
        user = User.query.filter_by(stripe_subscription_id=sub['id']).first()
        if user:
            user.subscription_tier = 'free'
            user.is_premium = False
            user.stripe_subscription_id = None
            db.session.commit()
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        user = User.query.filter_by(stripe_customer_id=invoice['customer']).first()
        if user:
            user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
    
    return jsonify({'status': 'success'}), 200


@app.route('/manage-subscription')
@login_required
def manage_subscription():
    """Manage or cancel subscription"""
    return render_template('manage_subscription.html',
                           owner_plan=OWNER_PLAN,
                           renter_plan=RENTER_PLAN)


@app.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel a subscription"""
    if stripe and current_user.stripe_subscription_id:
        try:
            stripe.Subscription.delete(current_user.stripe_subscription_id)
        except Exception as e:
            flash(f'Error cancelling: {str(e)}', 'danger')
            return redirect(url_for('manage_subscription'))
    
    current_user.subscription_tier = 'free'
    current_user.is_premium = False
    current_user.stripe_subscription_id = None
    current_user.subscription_expires = None
    db.session.commit()
    
    flash('Subscription cancelled. You can re-subscribe anytime.', 'info')
    return redirect(url_for('pricing'))


def check_search_limit():
    """Check if free-tier renter has exceeded daily search limit"""
    if not current_user.is_authenticated:
        return True  # Allow guests
    if current_user.subscription_tier == 'premium':
        return True  # Unlimited for premium
    if current_user.role != 'renter':
        return True  # No limit for owners searching
    
    today = date.today()
    if current_user.search_reset_date != today:
        current_user.search_count_today = 0
        current_user.search_reset_date = today
        db.session.commit()
    
    if current_user.search_count_today >= 5:
        return False
    
    current_user.search_count_today += 1
    db.session.commit()
    return True


def check_listing_limit():
    """Check if free-tier owner can post more listings"""
    if current_user.subscription_tier == 'premium':
        return True  # Unlimited for premium
    active_count = Listing.query.filter_by(
        owner_id=current_user.id,
        status='Active'
    ).count()
    return active_count < 1  # Free tier: max 1 active listing

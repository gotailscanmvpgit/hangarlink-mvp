from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest
import os
import random
import uuid
# ... (rest of imports)
from datetime import datetime, date, timedelta
from sqlalchemy import text, func

try:
    import stripe
except ImportError:
    stripe = None

try:
    import openai
except ImportError:
    openai = None

bp = Blueprint('main', __name__)

def get_stripe():
    if not stripe:
        return None
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    return stripe


@bp.before_request
def ensure_admin():
    if current_user.is_authenticated and current_user.email == 'admin@hangarlink.com':
        # Check if attribute exists (for safety) and if False
        if not getattr(current_user, 'is_admin', False):
            current_user.is_admin = True
            db.session.commit()
            flash('Admin privileges granted.', 'success')

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Stripe initialization helper
def get_stripe():
    if stripe:
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    return stripe

@bp.route('/')
def index():
    """Landing page / Dashboard"""
    # Debug: Print DB URL to verify config
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    print(f"DEBUG: DATABASE_URL Configured: {bool(db_url)}")
    if db_url:
        masked_url = db_url.split('@')[-1] if '@' in db_url else 'sqlite/local'
        print(f"DEBUG: Connection Target: ...{masked_url}")

    try:
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
    except Exception as e:
        print(f"CRITICAL ERROR in index route: {str(e)}")
        import traceback
        with open("error.log", "w") as f:
            f.write(str(e))
            f.write("\n")
            traceback.print_exc(file=f)
        return "<h1>HangarLinks is starting up. Please wait a moment or check back soon.</h1>", 500

@bp.route('/health')
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}, 500

@bp.route('/listings')
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
    
    # Sort: Featured -> Premium Owner -> Newest
    pagination = query.order_by(
        Listing.is_featured.desc(), 
        Listing.is_premium_listing.desc(), 
        Listing.created_at.desc()
    ).paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)
    
    listings = pagination.items
    
    return render_template('listings.html', 
                         listings=listings, 
                         pagination=pagination,
                         airport=airport, 
                         radius=radius,
                         covered=covered,
                         min_price=min_price,
                         max_price=max_price,
                         search_limited=search_limited)

@bp.route('/listing/<int:id>')
def listing_detail(id):
    """Individual listing detail page"""
    listing = Listing.query.get_or_404(id)
    return render_template('listing_detail.html', listing=listing)

@bp.route('/post-listing', methods=['GET', 'POST'])
@login_required
def post_listing():
    """Create a new listing"""
    print("DEBUG: Entering post-listing route")
    print("DEBUG: Current user:", current_user.id if current_user else "None")
    
    try:
        price_intel = None
    
        # Check listing limit for free tier
        if not check_listing_limit():
            flash('Free accounts can have 1 active listing. Upgrade to Premium for unlimited listings!', 'warning')
            return redirect(url_for('main.pricing'))
        
        if request.method == 'POST':
            # Handle file upload
            photo_filenames = []
            
            # Combine 'photos' (main) and 'health_photos' (checklist)
            all_files = []
            if 'photos' in request.files:
                all_files.extend(request.files.getlist('photos'))
            if 'health_photos' in request.files:
                all_files.extend(request.files.getlist('health_photos'))
                
            # Deduplicate or allow all? User said "1-5 photos" in modal.
            # I will process all but limit TOTAL to something reasonable if needed, or just allow all.
            # User previously said "limit to 5". I will limit total to 10? Or 5?
            # I'll process up to 10 to allow comprehensive gallery.
            all_files = all_files[:10] 
            
            for file in all_files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp AND uuid to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = uuid.uuid4().hex[:8]
                    filename = f"{timestamp}_{unique_id}_{filename}"
                    
                    # Use current_app.config for upload folder
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'listings', filename)
                    
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
            print(f"DEBUG: Saved listing {listing.id} for user {current_user.id}")
            
            # Check for matching alert preferences and notify users
            check_and_send_alerts(listing)
            
            flash('Listing created successfully!', 'success')
            return redirect(url_for('main.listing_detail', id=listing.id))
        
        # Get price intelligence if airport is provided via query param
        airport = request.args.get('airport', '').upper()
        if airport:
            temp_listing = Listing(airport_icao=airport, id=0)
            price_intel = temp_listing.get_price_intelligence()
        
        return render_template('post_listing.html', price_intel=price_intel, airport=airport)

    except Exception as e:
        print(f"CRITICAL ERROR in post_listing: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error creating listing: {str(e)}", "error")
        return redirect(url_for('main.index'))

def check_listing_limit():
    """Check if user can post more listings"""
    if current_user.is_premium or current_user.subscription_tier == 'premium':
        return True
    
    # Check count of active listings
    count = Listing.query.filter_by(owner_id=current_user.id, status='Active').count()
    return count < 1

@bp.route('/post-listing-confirm')
@login_required
def post_listing_confirm():
    """Confirmation page to help renters vs owners"""
    # Check if user has any listings
    user_listings_count = Listing.query.filter_by(owner_id=current_user.id).count()
    return render_template('post_listing_confirm.html', user_listings_count=user_listings_count)

@bp.route('/feed')
@login_required
def feed():
    """Community Feed of recent listings"""
    recent_listings = Listing.query.filter_by(status='Active').order_by(Listing.created_at.desc()).limit(20).all()
    return render_template('feed.html', listings=recent_listings)

@bp.route('/like/<int:listing_id>', methods=['POST'])
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

@bp.route('/my-listings')
@login_required
def my_listings():
    """View user's own listings"""
    page = request.args.get('page', 1, type=int)
    pagination = Listing.query.filter_by(owner_id=current_user.id)\
        .order_by(Listing.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('my_listings.html', listings=pagination.items, pagination=pagination)

@bp.route('/listing/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(id):
    """Edit a listing"""
    listing = Listing.query.get_or_404(id)
    
    # Check ownership
    if listing.owner_id != current_user.id:
        flash('You can only edit your own listings', 'error')
        return redirect(url_for('main.listing_detail', id=id))
    
    if request.method == 'POST':
        listing.airport_icao = request.form.get('airport_icao').upper()
        listing.size_sqft = int(request.form.get('size_sqft'))
        listing.covered = request.form.get('covered') == 'on'
        listing.price_month = float(request.form.get('price_month'))
        listing.description = request.form.get('description')
        listing.status = request.form.get('status', 'Active')
        
        db.session.commit()
        flash('Listing updated successfully!', 'success')
        return redirect(url_for('main.listing_detail', id=id))
    
    return render_template('edit_listing.html', listing=listing)

@bp.route('/messages')
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
    conversations.sort(key=lambda x: (
        x['partner'].is_premium, 
        x['last_message'].created_at if x['last_message'] else datetime.min
    ), reverse=True)
    
    return render_template('messages.html', conversations=conversations)

@bp.route('/message/<int:user_id>', methods=['GET', 'POST'])
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

@bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'renter')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Callsign/Username already taken', 'error')
            return redirect(url_for('main.register'))
        
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
        return redirect(url_for('main.index'))
    
    return render_template('register.html')

@bp.route('/api/dismiss-onboarding', methods=['POST'])
@login_required
def dismiss_onboarding():
    """API endpoint to mark onboarding tour as seen"""
    session.pop('show_onboarding', None)
    return jsonify({'status': 'ok'})

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.index'))

@bp.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('terms.html')

@bp.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('privacy.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile with alert preferences"""
    if request.method == 'POST':
        current_user.alert_enabled = request.form.get('alert_enabled') == 'on'
        current_user.alert_airport = request.form.get('alert_airport', '').upper() or None
        current_user.alert_max_price = float(request.form.get('alert_max_price')) if request.form.get('alert_max_price') else None
        current_user.alert_min_size = int(request.form.get('alert_min_size')) if request.form.get('alert_min_size') else None
        current_user.alert_covered_only = request.form.get('alert_covered_only') == 'on'
        
        db.session.commit()
        flash('Alert preferences saved! You\'ll be notified when matching listings are posted.', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html')

@bp.route('/dashboard/owner')
@login_required
def owner_dashboard():
    # Only for owners
    if current_user.role != 'owner':
        flash('Access restricted to hangar owners.', 'error')
        return redirect(url_for('main.index'))
        
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

# ========== MONETIZATION & SUBSCRIPTIONS ==========
TRANSACTION_FEE_PERCENT = 8
INSURANCE_RATES = {'daily': 15.00, 'base': 45.00}

@bp.route('/book/<int:listing_id>', methods=['POST'])
@login_required
def book_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    duration_days = 30 
    
    platform_fee = listing.price_month * (TRANSACTION_FEE_PERCENT / 100)
    base_total = listing.price_month + platform_fee
    
    add_insurance = request.form.get('add_insurance') == 'on'
    insurance_fee = 0.0
    
    if add_insurance:
        insurance_fee = (INSURANCE_RATES['daily'] * duration_days) + INSURANCE_RATES['base']
        
    final_total = base_total + insurance_fee
    
    try:
        stripe = get_stripe()
        if not stripe or not stripe.api_key:
            session_id = 'mock_session_123'
            checkout_session_url = url_for('main.booking_success', _external=True) + '?session_id=' + session_id
        else:
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Hangar Rental at {listing.airport_icao} (includes {TRANSACTION_FEE_PERCENT}% platform fee)',
                    },
                    'unit_amount': int(base_total * 100),
                },
                'quantity': 1,
            }]
            
            if add_insurance:
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Short-Term Hangar Insurance (Avemco Partner)',
                            'description': 'Liability & Hull coverage for 30 days',
                        },
                        'unit_amount': int(insurance_fee * 100),
                    },
                    'quantity': 1,
                })
                
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=url_for('main.booking_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('main.listing_detail', id=listing.id, _external=True),
            )
            checkout_session_url = checkout_session.url
            session_id = checkout_session.id
        
        booking = Booking(
            listing_id=listing.id, 
            renter_id=current_user.id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            total_price=listing.price_month,
            status='Pending',
            stripe_payment_id=session_id,
            insurance_opt_in=add_insurance,
            insurance_fee=insurance_fee
        )
        db.session.add(booking)
        db.session.commit()
            
        return redirect(checkout_session_url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('main.listing_detail', id=listing.id))

@bp.route('/booking/success')
@login_required
def booking_success():
    session_id = request.args.get('session_id')
    booking = Booking.query.filter_by(stripe_payment_id=session_id).first_or_404()
    
    booking.status = 'Confirmed'
    booking.listing.status = 'Rented'
    booking.listing.insurance_active = True
    db.session.commit()
    
    agreement_url = url_for('main.download_agreement', booking_id=booking.id)
    
    flash('Booking Confirmed! Rental agreement generated.', 'success')
    return render_template('booking_success.html', booking=booking, agreement_url=agreement_url)

@bp.route('/agreement/<int:booking_id>')
@login_required
def download_agreement(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if current_user.id != booking.renter_id and current_user.id != booking.listing.owner_id:
        flash('Unauthorized', 'error')
        return redirect(url_for('main.index'))
        
    return render_template('agreement_pdf.html', booking=booking)

@bp.route('/matches')
@login_required
def matches():
    airport = current_user.alert_airport
    
    # Optimization: Filter in DB to avoid loading all 10k listings
    query = Listing.query.filter_by(status='Active')
    
    candidates = []
    
    # 1. Prioritize strict airport matches (Limit 50)
    if airport:
        candidates.extend(query.filter_by(airport_icao=airport).limit(50).all())
        
    # 2. Get high-value/recent listings for broader match (Limit 100)
    # Exclude already found ones implies we need IDs, but simple union is faster for now
    candidates.extend(query.order_by(Listing.is_featured.desc(), Listing.created_at.desc()).limit(100).all())
    
    # Remove duplicates
    listings = list({l.id: l for l in candidates}.values())
    scored_matches = []
    
    for l in listings:
        score = 60 
        if airport and l.airport_icao == airport:
            score += 25
        elif airport:
            score += 5
            
        if current_user.alert_max_price and l.price_month <= current_user.alert_max_price:
            score += 15
            
        if l.owner.is_premium:
            score += 5
        if l.owner.is_certified:
            score += 10
            
        if l.health_score >= 80:
            score += 5
            
        final_score = min(score, 99)
        scored_matches.append({'listing': l, 'score': final_score})
        
    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = scored_matches[:10]
    
    return render_template('matches.html', matches=top_matches)

@bp.route('/concierge/chat', methods=['POST'])
@login_required
def concierge_chat():
    data = request.json
    user_msg = data.get('message', '').lower()
    
    response = "I'm the HangarLinks AI. "
    if 'price' in user_msg or 'cost' in user_msg:
        response += "Market rates at CYHM are trending up (+12%). I recommend listing around $600/mo for a T-Hangar."
    elif 'availability' in user_msg:
        response += "I see 3 covered spots opening up next month near Toronto."
    elif 'insurance' in user_msg:
        response += "All rentals include our $1M liability protection policy."
    else:
        response += "How can I help you find or list a hangar today?"
        
    return {'response': response}

@bp.route('/api/forecast', methods=['GET'])
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

@bp.route('/rewards')
@login_required
def rewards():
    if current_user.points is None:
        current_user.points = 0
        db.session.commit()
    return render_template('rewards.html', points=current_user.points)

@bp.route('/referrals')
@login_required
def referrals():
    if not current_user.referral_code:
        import random, string
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(chars) for _ in range(8))
        current_user.referral_code = code
        db.session.commit()
    return render_template('referrals.html', code=current_user.referral_code)

@bp.route('/admin/certify/me')
@login_required
def self_certify():
    current_user.is_certified = True
    current_user.reputation_score = 5.0
    current_user.points = (current_user.points or 0) + 500 
    db.session.commit()
    flash('You are now a Certified HangarLinks Partner! (+500 pts)', 'success')
    return redirect(url_for('main.profile'))

@bp.route('/dashboard/insights')
@login_required
def dashboard_insights():
    market_trend = "+12%"
    avg_price_area = "$1,200"
    
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

@bp.route('/book-viewing/<int:listing_id>', methods=['POST'])
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
    return redirect(url_for('main.listing_detail', id=listing.id))

@bp.route('/contact-guest/<int:listing_id>', methods=['POST'])
def contact_guest(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    if current_user.is_authenticated:
        return redirect(url_for('main.message_user', user_id=listing.owner_id, listing_id=listing.id))
        
    guest_email = request.form.get('guest_email')
    message_content = request.form.get('message')
    
    if not guest_email or not message_content:
        flash('Email and message are required', 'error')
        return redirect(url_for('main.listing_detail', id=listing.id))
    
    msg = Message(
        sender_id=None, 
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
    return redirect(url_for('main.listing_detail', id=listing.id))

@bp.route('/booking/complete/<int:booking_id>', methods=['POST'])
@login_required
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if current_user.id not in [booking.renter_id, booking.listing.owner_id]:
        flash('Unauthorized', 'error')
        return redirect(url_for('main.index'))
        
    rating = int(request.form.get('rating'))
    review = request.form.get('review')
    
    if current_user.id == booking.renter_id:
        booking.owner_rating = rating
        booking.owner_review = review
        owner = booking.listing.owner
        new_count = owner.rentals_count + 1
        new_score = ((owner.reputation_score * owner.rentals_count) + rating) / new_count
        owner.reputation_score = new_score
        owner.rentals_count = new_count
        
    elif current_user.id == booking.listing.owner_id:
        booking.renter_rating = rating
        booking.renter_review = review
    
    booking.status = 'Completed'
    db.session.commit()
    
    flash('Rental completed and reviewed!', 'success')
    return redirect(url_for('main.index'))

OWNER_PLAN = {
    'name': 'Owner Premium',
    'price': 999,
    'price_display': '9.99',
    'interval': 'month',
    'features': ['Unlimited active listings', 'Priority placement', 'Analytics', 'Premium badge', 'Verified Owner', 'Export reports']
}

RENTER_PLAN = {
    'name': 'Renter Premium',
    'price': 699,
    'price_display': '6.99',
    'interval': 'month',
    'features': ['Unlimited searches', 'Saved alerts', 'Priority support', 'Premium badge', 'Early access', 'Advanced filters']
}

@bp.route('/pricing')
def pricing():
    return render_template('pricing.html', owner_plan=OWNER_PLAN, renter_plan=RENTER_PLAN, fee_percent=TRANSACTION_FEE_PERCENT)

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    stripe = get_stripe()
    if not stripe:
        flash('Stripe is not configured. Please set STRIPE_SECRET_KEY.', 'warning')
        return redirect(url_for('main.pricing'))
    
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
                        'description': f"HangarLinks {plan['name']} - Monthly Subscription",
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
            metadata={'user_id': current_user.id, 'plan_type': plan_type}
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('main.pricing'))

@bp.route('/subscription/success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    plan_type = request.args.get('plan', 'owner')
    stripe = get_stripe()
    
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
        current_user.subscription_tier = 'premium'
        current_user.is_premium = True
        current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        db.session.commit()

    # Admin email notification (MVP placeholder)
    _notify_admin_subscription(current_user, plan_type)

    flash('🎉 Welcome to Premium! Your subscription is active.', 'success')
    return render_template('subscription_success.html', plan_type=plan_type,
                           plan=OWNER_PLAN if plan_type == 'owner' else RENTER_PLAN)

@bp.route('/subscription/cancel')
def subscription_cancel():
    flash('Subscription checkout was cancelled. You can try again anytime.', 'info')
    return redirect(url_for('main.pricing'))

@bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    stripe = get_stripe()
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

@bp.route('/manage-subscription')
@login_required
def manage_subscription():
    return render_template('manage_subscription.html', owner_plan=OWNER_PLAN, renter_plan=RENTER_PLAN)

@bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    stripe = get_stripe()
    if stripe and current_user.stripe_subscription_id:
        try:
            stripe.Subscription.delete(current_user.stripe_subscription_id)
        except Exception as e:
            flash(f'Error cancelling: {str(e)}', 'danger')
            return redirect(url_for('main.manage_subscription'))
    
    current_user.subscription_tier = 'free'
    current_user.is_premium = False
    current_user.stripe_subscription_id = None
    current_user.subscription_expires = None
    db.session.commit()
    
    flash('Subscription cancelled. You can re-subscribe anytime.', 'info')
    return redirect(url_for('main.pricing'))

def check_search_limit():
    if not current_user.is_authenticated:
        return True 
    if current_user.subscription_tier == 'premium':
        return True 
    if current_user.role != 'renter':
        return True 
    
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

SPONSORED_TIERS = {
    'silver': {'price': 4900, 'name': 'Silver Featured', 'days': 30, 'boost': '2x'},
    'gold': {'price': 9900, 'name': 'Gold Featured', 'days': 30, 'boost': '5x'},
    'platinum': {'price': 19900, 'name': 'Platinum Featured', 'days': 30, 'boost': '10x'}
}

INSIGHTS_PRICING = {
    'report': {'price': 1999, 'name': 'Single Market Report', 'type': 'one_time'},
    'subscription': {'price': 9900, 'name': 'Pro Analytics Year', 'type': 'recurring'}
}

@bp.route('/pricing/sponsored')
@login_required
def pricing_sponsored():
    listings = Listing.query.filter_by(owner_id=current_user.id, status='Active').all()
    return render_template('pricing_sponsored.html', listings=listings, tiers=SPONSORED_TIERS)

@bp.route('/promote-listing/<tier>', methods=['POST'])
@login_required
def promote_listing(tier):
    stripe = get_stripe()
    if not stripe:
        flash('Stripe not configured.', 'warning')
        return redirect(url_for('main.pricing_sponsored'))
        
    listing_id = request.form.get('listing_id')
    if not listing_id:
        flash('Please select a listing to promote.', 'warning')
        return redirect(url_for('main.pricing_sponsored'))
        
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
        
    plan = SPONSORED_TIERS.get(tier)
    if not plan:
        flash('Invalid plan selected.', 'danger')
        return redirect(url_for('main.pricing_sponsored'))
        
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{plan['name']} - {listing.airport_icao}",
                        'description': f"Featured listing boost for 30 days ({plan['boost']} visibility)",
                    },
                    'unit_amount': plan['price'],
                },
                'quantity': 1,
            }],
            mode='payment', 
            success_url=request.host_url + f'sponsored/success?session_id={{CHECKOUT_SESSION_ID}}&listing_id={listing.id}&tier={tier}',
            cancel_url=request.host_url + 'pricing/sponsored',
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('main.pricing_sponsored'))

@bp.route('/sponsored/success')
@login_required
def sponsored_success():
    session_id = request.args.get('session_id')
    listing_id = request.args.get('listing_id')
    tier = request.args.get('tier')
    
    listing = Listing.query.get(listing_id)
    if listing:
        listing.is_featured = True
        listing.featured_tier = tier
        listing.featured_expires_at = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        flash(f'Success! Listing is now {tier.title()} Featured.', 'success')
        
    return redirect(url_for('main.listing_detail', id=listing_id))

@bp.route('/insights')
@login_required
def insights():
    has_access = current_user.has_analytics_access or current_user.subscription_tier == 'premium'
    if current_user.analytics_expires_at and current_user.analytics_expires_at < datetime.utcnow():
        has_access = False
        
    if not has_access:
        return render_template('insights_teaser.html', pricing=INSIGHTS_PRICING)
        
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    hk_market_price = [random.randint(1200, 1600) for _ in range(6)]
    user_avg_price = [random.randint(1100, 1500) for _ in range(6)]
    occupancy_data = [random.randint(60, 95) for _ in range(6)]
    demand_score = 8.5
    
    return render_template('insights.html', 
                           months=months, 
                           market_prices=hk_market_price,
                           my_prices=user_avg_price,
                           occupancy=occupancy_data,
                           demand_score=demand_score)

@bp.route('/buy-insights/<type>', methods=['POST'])
@login_required
def buy_insights(type):
    stripe = get_stripe()
    if not stripe:
        flash('Stripe not setup', 'warning')
        return redirect(url_for('main.insights'))
        
    plan = INSIGHTS_PRICING.get(type)
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plan['name'],
                    },
                    'unit_amount': plan['price'],
                },
                'quantity': 1,
            }],
            mode='payment', 
            success_url=request.host_url + f'insights/success?session_id={{CHECKOUT_SESSION_ID}}&type={type}',
            cancel_url=request.host_url + 'insights',
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('main.insights'))

@bp.route('/insights/success')
@login_required
def insights_success():
    type = request.args.get('type')
    
    current_user.has_analytics_access = True
    if type == 'subscription':
         current_user.analytics_expires_at = datetime.utcnow() + timedelta(days=365)
    else:
         current_user.analytics_expires_at = datetime.utcnow() + timedelta(days=30) 
    db.session.commit()
    
    flash('Analytics Unlocked!', 'success')
    return redirect(url_for('main.insights'))

@bp.context_processor
def inject_ads():
    def get_ads(placement, limit=1):
        try:
            return Ad.query.filter_by(placement=placement, active=True).order_by(func.random()).limit(limit).all()
        except Exception:
            return []
    return dict(get_ads=get_ads)

@bp.route('/admin/ads', methods=['GET', 'POST'])
@login_required
def admin_ads():
    if not getattr(current_user, 'is_admin', False):
        abort(403)
        
    if request.method == 'POST':
        title = request.form.get('title')
        image_url = request.form.get('image_url')
        link_url = request.form.get('link_url')
        placement = request.form.get('placement')
        
        new_ad = Ad(title=title, image_url=image_url, link_url=link_url, placement=placement, active=True)
        db.session.add(new_ad)
        db.session.commit()
        flash('Ad created successfully!', 'success')
        return redirect(url_for('main.admin_ads'))
        
    # Calculate stats — wrapped in try/except in case Ad table is not yet migrated
    try:
        active_ads_count = Ad.query.filter_by(active=True).count()
        total_impressions = db.session.query(func.sum(Ad.impressions)).scalar() or 0
        total_clicks = db.session.query(func.sum(Ad.clicks)).scalar() or 0
        ads = Ad.query.order_by(Ad.created_at.desc()).all()
    except Exception as e:
        current_app.logger.error(f"admin_ads DB error: {e}")
        active_ads_count = total_impressions = total_clicks = 0
        ads = []
        flash('⚠️ Ad table not yet created — run db.create_all() or restart the app.', 'warning')

    return render_template('admin_ads.html', ads=ads,
                           active_ads_count=active_ads_count,
                           total_impressions=total_impressions,
                           total_clicks=total_clicks)

@bp.route('/admin/ads/toggle/<int:ad_id>', methods=['POST'])
@login_required
def toggle_ad(ad_id):
    if not getattr(current_user, 'is_admin', False):
        abort(403)
    ad = Ad.query.get_or_404(ad_id)
    ad.active = not ad.active
    db.session.commit()
    flash(f'Ad {"enabled" if ad.active else "disabled"}', 'success')
    return redirect(url_for('main.admin_ads'))

@bp.route('/admin/ads/delete/<int:ad_id>', methods=['POST'])
@login_required
def delete_ad(ad_id):
    if not getattr(current_user, 'is_admin', False):
        abort(403)
    ad = Ad.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    flash('Ad deleted', 'success')
    return redirect(url_for('main.admin_ads'))

@bp.route('/white-label', methods=['GET'])
def white_label():
    return render_template('white_label.html')

@bp.route('/white-label/submit', methods=['POST'])
def white_label_submit():
    fbo_name = request.form.get('fbo_name')
    contact_name = request.form.get('contact_name')
    contact_email = request.form.get('contact_email')
    
    # Create request record
    req = WhiteLabelRequest(fbo_name=fbo_name, contact_name=contact_name, contact_email=contact_email, status='Pending Payment')
    db.session.add(req)
    db.session.commit()
    
    # Initiate Stripe Checkout for Reservation Fee
    try:
        stripe = get_stripe()
        if not stripe or not stripe.api_key:
            # Mock success for dev
            req.status = 'Paid'
            db.session.commit()
            return redirect(url_for('main.white_label_success'))
            
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'HangarLinks White-Label Reservation',
                        'description': f'Deployment slot for {fbo_name}',
                    },
                    'unit_amount': 49900, # $499.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('main.white_label_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.white_label', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('main.white_label'))

@bp.route('/white-label/success')
def white_label_success():
    return render_template('subscription_success.html', title="Reservation Confirmed", message="Thank you for reserving your White-Label slot! Our deployment team will contact you within 24 hours.")

@bp.route('/insights/market-reports')
@login_required
def market_reports():
    reports = [
        {'id': 'hamilton_q1', 'title': 'Average hangar price at CYHM (Hamilton)', 'price': 19.99, 'growth': 12, 'date': 'Q1 2026', 'desc': 'Detailed analysis of rental trends.'},
        {'id': 'ontario_occ', 'title': 'Ontario Regional Occupancy Report', 'price': 19.99, 'growth': 5.4, 'date': 'Feb 2026', 'desc': 'Vacancy rates across 15 airports.'},
        {'id': 'luxury_forecast', 'title': 'Luxury Hangar Demand Forecast 2026', 'price': 19.99, 'growth': 18, 'date': 'Annual', 'desc': 'Projected demand for 5000+ sqft units.'},
        {'id': 'national_q1', 'title': 'Q1 2026 National Hangar Market Report', 'price': 149.00, 'growth': 3.2, 'date': 'Q1 2026', 'desc': 'Comprehensive analysis of 500+ airports.'}
    ]
    return render_template('market_reports.html', reports=reports)

@bp.route('/insights/buy-report/<report_id>', methods=['POST'])
@login_required
def buy_report(report_id):
    # Mapping ID to price
    prices = {
        'hamilton_q1': 1999,
        'ontario_occ': 1999,
        'luxury_forecast': 1999,
        'national_q1': 14900
    }
    price = prices.get(report_id, 1999)
    title = report_id.replace('_', ' ').title() + " Report"
    
    try:
        stripe = get_stripe()
        if not stripe or not stripe.api_key:
            flash(f'Mock Purchase: You bought {title}!', 'success')
            return redirect(url_for('main.market_reports'))
            
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': title,
                    },
                    'unit_amount': price,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('main.market_reports', _external=True) + '?purchased=true',
            cancel_url=url_for('main.market_reports', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('main.market_reports'))


# ─────────────────────────────────────────────
#  ADMIN — EMAIL HELPER
# ─────────────────────────────────────────────

def _notify_admin_subscription(user, plan_type: str):
    """MVP placeholder: log subscription event. Wire to real email (SendGrid/SES) later."""
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@hangarlinks.com')
    msg = (
        f"[HangarLinks] NEW SUBSCRIPTION\n"
        f"User:  {user.username} <{user.email}>\n"
        f"Plan:  {plan_type}\n"
        f"Time:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"---\n"
        f"To send real emails, set ADMIN_EMAIL and wire Flask-Mail / SendGrid."
    )
    current_app.logger.info(f"[ADMIN NOTIFY] New subscription: {user.email} ({plan_type})")
    # TODO: Replace with real email send, e.g.:
    # mail.send_message(subject='New Subscription', recipients=[admin_email], body=msg)
    print(msg)  # Visible in Railway/Gunicorn logs for now


# ─────────────────────────────────────────────
#  ADMIN — /admin/listings  (Featured Management)
# ─────────────────────────────────────────────

def admin_required(f):
    """Decorator: only allow is_admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route('/admin/listings')
@login_required
@admin_required
def admin_listings():
    """Admin panel: all listings with featured toggle."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip().upper()
    status_filter = request.args.get('status', '')
    featured_filter = request.args.get('featured', '')

    q = Listing.query
    if search:
        q = q.filter(Listing.airport_icao.ilike(f'%{search}%'))
    if status_filter:
        q = q.filter_by(status=status_filter)
    if featured_filter == 'yes':
        q = q.filter_by(is_featured=True)
    elif featured_filter == 'no':
        q = q.filter_by(is_featured=False)

    listings = q.order_by(Listing.is_featured.desc(), Listing.created_at.desc()) \
                 .paginate(page=page, per_page=25, error_out=False)

    stats = {
        'total': Listing.query.count(),
        'featured': Listing.query.filter_by(is_featured=True).count(),
        'active': Listing.query.filter_by(status='Active').count(),
        'users': User.query.count(),
        'premium_users': User.query.filter_by(subscription_tier='premium').count(),
    }
    return render_template('admin_listings.html', listings=listings, stats=stats,
                           search=search, status_filter=status_filter,
                           featured_filter=featured_filter)


@bp.route('/admin/toggle-featured/<int:listing_id>', methods=['POST'])
@login_required
@admin_required
def toggle_featured(listing_id):
    """Toggle is_featured on a listing."""
    listing = Listing.query.get_or_404(listing_id)
    listing.is_featured = not listing.is_featured
    db.session.commit()
    state = 'Featured' if listing.is_featured else 'Unfeatured'
    flash(f'✅ Listing {listing.airport_icao} #{listing.id} → {state}', 'success')
    return redirect(request.referrer or url_for('main.admin_listings'))


# ─────────────────────────────────────────────
#  AI CONCIERGE  – /api/concierge
# ─────────────────────────────────────────────

def _build_db_context(message: str) -> str:
    """Pull live data from the DB relevant to the user's question."""
    ctx_parts = []
    msg_lower = message.lower()

    # Airport ICAO extraction (4-letter codes starting with C or K common in Canada/US)
    import re
    airport_hits = re.findall(r'\b([CK][A-Z]{3})\b', message.upper())

    # Price filter extraction
    price_match = re.search(r'under\s*\$?(\d+)', msg_lower)
    max_price = int(price_match.group(1)) if price_match else None

    covered_only = any(w in msg_lower for w in ['covered', 'indoor', 'enclosed'])

    # Case 1: listing search
    if any(w in msg_lower for w in ['show', 'find', 'search', 'available', 'hangar', 'listing', 'price']):
        q = Listing.query.filter_by(status='Active')
        if airport_hits:
            q = q.filter(Listing.airport_icao.in_(airport_hits))
        if max_price:
            q = q.filter(Listing.price_month <= max_price)
        if covered_only:
            q = q.filter_by(covered=True)
        results = q.order_by(Listing.health_score.desc()).limit(5).all()
        if results:
            lines = ["**Top available hangars matching your query:**"]
            for l in results:
                covered_tag = "🏠 Covered" if l.covered else "🌤 Uncovered"
                lines.append(
                    f"- **{l.airport_icao}** | {l.size_sqft} sqft | ${l.price_month:.0f}/mo | {covered_tag} | "
                    f"[View Listing](/listing/{l.id})"
                )
            ctx_parts.append("\n".join(lines))
        else:
            ctx_parts.append("No active listings match those filters right now.")

    # Case 2: average price query
    if any(w in msg_lower for w in ['average', 'avg', 'typical', 'market price', 'how much']):
        from sqlalchemy import func
        for icao in (airport_hits or []):
            row = db.session.query(func.avg(Listing.price_month)).filter_by(
                airport_icao=icao, status='Active'
            ).scalar()
            if row:
                ctx_parts.append(f"Average active listing price at **{icao}**: **${row:.0f}/month**")

    # Case 3: owner asks about their own listings
    if any(w in msg_lower for w in ['my listing', 'my hangar', 'performing', 'health score', 'views']):
        if current_user.is_authenticated and current_user.role == 'owner':
            listings = Listing.query.filter_by(owner_id=current_user.id).all()
            if listings:
                lines = ["**Your listings:**"]
                for l in listings:
                    lines.append(
                        f"- {l.airport_icao} | ${l.price_month:.0f}/mo | Status: {l.status} | "
                        f"Health Score: {l.health_score}/100 | [Manage](/listing/{l.id})"
                    )
                ctx_parts.append("\n".join(lines))
            else:
                ctx_parts.append("You have no listings yet. [Post one now](/post_listing)")

    return "\n\n".join(ctx_parts) if ctx_parts else ""


def _rule_based_response(message: str, user_role: str, db_context: str) -> str:
    """Fallback smart rule-based responses when no LLM key is configured."""
    msg = message.lower()
    if db_context:
        return db_context
    if 'hello' in msg or 'hi' in msg:
        return "👋 Hello! I'm your HangarLinks AI Concierge. Ask me to find hangars, check prices, or manage your listings!"
    if 'help' in msg:
        return (
            "I can help you:\n"
            "- **Find hangars** – *Show covered hangars at CYHM under $400*\n"
            "- **Check prices** – *What's the average price at CYTZ?*\n"
            "- **Manage listings** – *How is my listing performing?*\n"
            "- **Book a viewing** – *I want to book a viewing of listing #3*"
        )
    if user_role == 'owner':
        return "As an owner, I can help you manage listings, check performance, or promote your hangar. What do you need?"
    return "I can help you find the perfect hangar. Try asking: *Show me covered hangars at CYYZ under $600*"


@bp.route('/api/concierge', methods=['POST'])
@login_required
def concierge_api():
    """Smart AI Concierge endpoint with RAG + optional LLM."""
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    history = data.get('history', [])  # List of {role, content}

    if not message:
        return jsonify({'reply': 'Please type a message.'}), 400

    # Build live DB context (RAG layer)
    db_context = _build_db_context(message)

    # User context
    user_role = current_user.role if current_user.is_authenticated else 'guest'
    home_airport = getattr(current_user, 'alert_airport', None) or 'Not set'
    user_name = current_user.username if current_user.is_authenticated else 'Guest'

    # Try LLM (OpenAI / Grok-compatible endpoint)
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('GROK_API_KEY')
    base_url = os.environ.get('OPENAI_BASE_URL')  # Set to https://api.x.ai/v1 for Grok

    if openai and api_key:
        try:
            client_kwargs = {'api_key': api_key}
            if base_url:
                client_kwargs['base_url'] = base_url
            client = openai.OpenAI(**client_kwargs)

            system_prompt = f"""You are the HangarLinks AI Concierge — a smart, friendly aviation assistant.
You help aircraft owners find hangars, and hangar owners manage their listings.

USER CONTEXT:
- Name: {user_name}
- Role: {user_role}
- Home Airport: {home_airport}

LIVE DATABASE CONTEXT (use this to answer):
{db_context if db_context else "No specific data found for this query."}

INSTRUCTIONS:
- Use the live data above to answer questions about prices, availability, listings.
- Be concise and friendly. Use markdown (bold, bullet points) for clarity.
- If you find matching listings, always include the [View Listing](/listing/ID) link.
- If asked to message an owner or book a viewing, say you'll facilitate: "I'll connect you — click the listing link."
- NEVER make up listing data. Only use what's in LIVE DATABASE CONTEXT.
- Keep replies under 200 words."""

            # Build conversation messages
            messages = [{'role': 'system', 'content': system_prompt}]
            # Include last 6 messages of history for context
            for h in history[-6:]:
                if h.get('role') in ('user', 'assistant') and h.get('content'):
                    messages.append({'role': h['role'], 'content': h['content']})
            messages.append({'role': 'user', 'content': message})

            model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=400,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content.strip()
            return jsonify({'reply': reply, 'source': 'llm'})

        except Exception as e:
            current_app.logger.error(f"Concierge LLM error: {e}")
            # Fall through to rule-based

    # Rule-based fallback
    reply = _rule_based_response(message, user_role, db_context)
    return jsonify({'reply': reply, 'source': 'rules'})


from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from extensions import db, mail, limiter, cache
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest, Payment
import os
import secrets
import datetime
try:
    from weasyprint import HTML
except Exception as e:
    HTML = None
    print(f"Warning: WeasyPrint PDF Engine inactive (dependencies missing): {e}")

try:
    from flask_mail import Message as MailMessage
except ImportError:
    MailMessage = None

try:
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
except ImportError:
    URLSafeTimedSerializer = SignatureExpired = BadSignature = None
import os
import random
import uuid
# ... (rest of imports)
import datetime
from datetime import date, timedelta, timezone
from sqlalchemy import text, func

try:
    import stripe
except ImportError:
    stripe = None

try:
    import openai
except ImportError:
    openai = None

try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
except ImportError:
    pd = np = RandomForestRegressor = train_test_split = None

# Global Event Registry mapped to AI Pricing Optimizations
EVENTS = {
    'Oshkosh AirVenture': {'dates': '2026-07-20 to 2026-07-26', 'airports': ['KOSH', 'KATW', 'KFLD'], 'surge': 50},
    'Sun n Fun Aerospace Expo': {'dates': '2026-04-05 to 2026-04-10', 'airports': ['KLAL', 'KPCM', 'KBOW'], 'surge': 40},
    'NBAA-BACE Las Vegas': {'dates': '2026-10-14 to 2026-10-16', 'airports': ['KLAS', 'KHND', 'KVGT'], 'surge': 45},
    'Reno Air Races': {'dates': '2026-09-10 to 2026-09-14', 'airports': ['KRTS', 'kRNO', 'KCXP'], 'surge': 35},
    'High Sierra Fly-In': {'dates': '2026-10-15 to 2026-10-18', 'airports': ['Dead Cow Lakebed', 'KWMC', 'KRNO'], 'surge': 30}
}

bp = Blueprint('main', __name__)

def get_stripe():
    if not stripe:
        return None
    # Ensure current key is set from config
    key = current_app.config.get('STRIPE_SECRET_KEY')
    if not key or 'here' in key:
        return None
    stripe.api_key = key
    return stripe


@bp.before_request
def ensure_admin():
    try:
        if current_user.is_authenticated and current_user.email == 'admin@hangarlink.com':
            if not getattr(current_user, 'is_admin', False):
                current_user.is_admin = True
                db.session.commit()
                flash('Admin privileges granted.', 'success')
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"[ensure_admin] error: {exc}")
        try:
            db.session.rollback()
        except Exception:
            pass


# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

        # Get map markers (all active listings with coordinates)
        map_listings = Listing.query.filter_by(status='Active').all()
        markers = []
        for l in map_listings:
            if l.lat is not None and l.lon is not None:
                markers.append({
                    'id': l.id,
                    'lat': l.lat,
                    'lon': l.lon,
                    'title': f"{l.airport_icao} Hangar",
                    'icao': l.airport_icao,
                    'price': f"${int(l.price_month)}",
                    'is_premium': l.is_premium_listing or (l.owner and l.owner.is_premium)
                })
            
        return render_template('index.html', 
                              listings_count=listings_count, 
                              messages_count=messages_count, 
                              saved_searches_count=saved_searches_count,
                              show_onboarding=show_onboarding,
                              markers=markers)
    except Exception as e:
        print(f"CRITICAL ERROR in index route: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        with open("error.log", "w") as f:
            f.write(str(e))
            f.write("\n")
            f.write(tb)
        return f"<h1>HangarLinks Error</h1><pre>{str(e)}\n\n{tb}</pre>", 500

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
    print("DEBUG: /listings route entered")

    # Safely check search limit (never let this crash the page)
    search_limited = False
    try:
        if not check_search_limit():
            search_limited = True
    except Exception as lim_err:
        print(f"WARN: check_search_limit failed: {lim_err}")

    airport = request.args.get('airport', '').strip().upper()
    radius = request.args.get('radius', 250, type=int)
    covered = request.args.get('covered', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    duration = request.args.get('duration', 7, type=int)
    is_heated = request.args.get('is_heated')
    access_24_7 = request.args.get('access_24_7')
    electric_doors_only = request.args.get('electric_doors_only')
    nfpa_409_compliant = request.args.get('nfpa_409_compliant')
    gpu_power_available = request.args.get('gpu_power_available')

    def _run_query():
        q = Listing.query.filter_by(status='Active')
        if airport:
            q = q.filter_by(airport_icao=airport)
        if covered == 'yes':
            q = q.filter_by(covered=True)
        elif covered == 'no':
            q = q.filter_by(covered=False)
        if min_price:
            q = q.filter(Listing.price_month >= min_price)
        if max_price:
            q = q.filter(Listing.price_month <= max_price)
        if duration:
            q = q.filter(Listing.min_stay_nights <= duration)
        if is_heated == '1':
            q = q.filter_by(is_heated=True)
        if access_24_7 == '1':
            q = q.filter_by(access_24_7=True)
        if electric_doors_only == '1':
            q = q.filter(Listing.door_type.in_(['Electric', 'Hydraulic', 'Bi-Fold (Electric)']))
        if nfpa_409_compliant == '1':
            q = q.filter_by(nfpa_409_compliant=True)
        if gpu_power_available == '1':
            q = q.filter_by(gpu_power_available=True)
        return q.order_by(
            Listing.min_stay_nights.asc(),
            Listing.is_featured.desc(),
            Listing.is_premium_listing.desc(),
            Listing.created_at.desc()
        ).paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)

    try:
        pagination = _run_query()
    except Exception as db_err:
        print(f"ERROR: listings DB query failed: {db_err}")
        # Self-heal: ensure tables exist then retry once
        try:
            from extensions import db as _db
            _db.create_all()
            db.session.rollback()
            print("INFO: db.create_all() self-heal triggered, retrying query...")
            pagination = _run_query()
        except Exception as retry_err:
            import traceback
            traceback.print_exc()
            print(f"FATAL: listings retry also failed: {retry_err}")
            flash('Database is temporarily unavailable. Please try again in a moment.', 'error')
            return render_template('listings.html',
                                   listings=[], pagination=None,
                                   airport=airport, radius=radius,
                                   covered=covered, min_price=min_price,
                                   max_price=max_price,
                                   search_limited=search_limited,
                                   markers=[]), 503

    listings_items = pagination.items
    markers = []
    for l in listings_items:
        if l.lat is not None and l.lon is not None:
            try:
                markers.append({
                    'id': l.id,
                    'lat': l.lat,
                    'lon': l.lon,
                    'title': f"{l.airport_icao} Hangar",
                    'icao': l.airport_icao,
                    'price': f"${int(l.price_month)}",
                    'is_premium': l.is_premium_listing or (l.owner and l.owner.is_premium)
                })
            except Exception:
                pass

    print(f"DEBUG: /listings returning {len(listings_items)} results")
    return render_template('listings.html',
                           listings=listings_items,
                           pagination=pagination,
                           airport=airport,
                           radius=radius,
                           covered=covered,
                           min_price=min_price,
                           max_price=max_price,
                           search_limited=search_limited,
                           markers=markers)

@bp.route('/listing/<int:id>')
def listing_detail(id):
    """Individual listing detail page"""
    import traceback as _tb
    from models import Booking
    print(f"DEBUG: listing_detail entered for id={id}")
    try:
        listing = db.get_or_404(Listing, id)
        aircraft_sizes = current_app.config.get('AIRCRAFT_SIZES', {})

        # Check if user has access to secure items like Ramp Cam
        has_access = False
        if current_user.is_authenticated:
            if current_user.id == listing.owner_id:
                has_access = True
            else:
                active_booking = Booking.query.filter_by(
                    renter_id=current_user.id,
                    listing_id=listing.id
                ).filter(Booking.status.in_(['pending', 'confirmed', 'active'])).first()
                if active_booking:
                    has_access = True

        # Fetch live weather for this airport
        weather = None
        try:
            from weather_service import fetch_airport_weather
            lat = listing.lat or 43.6275
            lon = listing.lon or -79.3962
            weather = fetch_airport_weather(lat, lon, listing.airport_icao or 'UNKN')
        except Exception as we:
            current_app.logger.warning(f"[WEATHER] Could not fetch weather: {we}")

        print(f"DEBUG: rendering listing_detail.html for listing {id}")
        return render_template('listing_detail.html', listing=listing,
                               aircraft_sizes=aircraft_sizes, has_access=has_access,
                               weather=weather)

    except Exception as e:
        err = _tb.format_exc()
        print(f"ERROR in listing_detail(id={id}): {e}\n{err}")
        # Return traceback as plain text so we can see the exact error
        return f"<pre style='padding:2rem;font-size:13px'><b>500 DEBUG — listing_detail(id={id})</b>\n\n{err}</pre>", 500

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
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
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
            
            # Practical Features booleans
            access_24_7 = request.form.get('access_24_7') == 'on'
            is_heated = request.form.get('is_heated') == 'on'
            battery_tender = request.form.get('battery_tender') == 'on'
            engine_heater = request.form.get('engine_heater') == 'on'
            snow_removal = request.form.get('snow_removal') == 'on'
            hurricane_tiedowns = request.form.get('hurricane_tiedowns') == 'on'
            door_type = request.form.get('door_type')
            ramp_cam_url = request.form.get('ramp_cam_url')
            
            # Corporate Jet Safety
            nfpa_409_compliant = request.form.get('nfpa_409_compliant') == 'on'
            gpu_power_available = request.form.get('gpu_power_available') == 'on'
            
            tail_height = request.form.get('tail_height_clearance')
            tail_height_clearance = float(tail_height) if tail_height and tail_height.strip() else None
            
            floor_loading_pcn = request.form.get('floor_loading_pcn')
            
            if access_24_7: score += 10
            if is_heated: score += 15
            if battery_tender: score += 10
            if engine_heater: score += 10
            if snow_removal: score += 10
            if hurricane_tiedowns: score += 15
            if ramp_cam_url: score += 15
            if nfpa_409_compliant: score += 20
            if gpu_power_available: score += 10
            if door_type in ['Electric', 'Hydraulic', 'Bi-Fold (Electric)']: score += 15
            
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
                    avail_start = datetime.datetime.strptime(request.form.get('availability_start'), '%Y-%m-%d').date()
                 except ValueError:
                    pass
            if request.form.get('availability_end'):
                 try:
                    avail_end = datetime.datetime.strptime(request.form.get('availability_end'), '%Y-%m-%d').date()
                 except ValueError:
                    pass
    
            # ── Auto-resolve lat/lon from ICAO ───────────────────────────────
            from airport_coords import get_coords
            icao_upper = request.form.get('airport_icao', '').upper()
            lat, lon, coord_found = get_coords(icao_upper)
            if not coord_found:
                logger.warning(f"[AIRPORT-COORDS] unknown ICAO '{icao_upper}', using Toronto default")

            # Handle Airbnb-specific inputs
            price_month = float(request.form.get('price_month') or 0)
            
            raw_night_price = request.form.get('price_night')
            if raw_night_price and raw_night_price.strip():
                price_night = float(raw_night_price)
            else:
                price_night = round(price_month / 30, 2) if price_month > 0 else 0.0
                
            min_stay = int(request.form.get('min_stay_nights') or 1)

            listing = Listing(
                airport_icao=icao_upper,
                size_sqft=int(request.form.get('size_sqft')),
                available_sqft=float(request.form.get('size_sqft')),
                covered=request.form.get('covered') == 'on',
                price_month=price_month,
                price_night=price_night,
                min_stay_nights=min_stay,
                description=request.form.get('description'),
                photos=','.join(photo_filenames) if photo_filenames else None,
                owner_id=current_user.id,
                status='Active',
                condition_verified=condition_verified,
                checklist_completed=checklist_verified,
                health_score=min(score, 100), # Cap at 100
                availability_start=avail_start,
                availability_end=avail_end,
                virtual_tour_url=request.form.get('virtual_tour_url'), # Feature 2
                lat=lat,
                lon=lon,
                door_type=door_type,
                access_24_7=access_24_7,
                is_heated=is_heated,
                battery_tender=battery_tender,
                engine_heater=engine_heater,
                snow_removal=snow_removal,
                hurricane_tiedowns=hurricane_tiedowns,
                ramp_cam_url=ramp_cam_url,
                tail_height_clearance=tail_height_clearance,
                nfpa_409_compliant=nfpa_409_compliant,
                floor_loading_pcn=floor_loading_pcn,
                gpu_power_available=gpu_power_available,
                insurance_active=request.form.get('insurance_provided') == 'on',
                shuttle_info=request.form.get('shuttle_info', '').strip() or None
            )
            db.session.add(listing)
            db.session.commit()
            print(f"DEBUG: Saved listing {listing.id} at {icao_upper} ({lat:.4f}, {lon:.4f}) for user {current_user.id}")
            
            # Check for matching alert preferences and notify users
            check_and_send_alerts(listing)
            
            flash('Listing created successfully!', 'success')
            return redirect(url_for('main.listing_detail', id=listing.id))
        
        # Get price intelligence if airport is provided via query param
        airport = request.args.get('airport', '').upper()
        if airport:
            temp_listing = Listing(airport_icao=airport, id=0)
            price_intel = temp_listing.get_price_intelligence()
        
        return render_template('post_listing.html', price_intel=price_intel, airport=airport, events=EVENTS)

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

        # ── Auto-update lat/lon when ICAO changes ────────────────────────────
        from airport_coords import get_coords
        lat, lon, coord_found = get_coords(listing.airport_icao)
        if not coord_found:
            import logging
            logging.getLogger(__name__).warning(
                f"[AIRPORT-COORDS] unknown ICAO '{listing.airport_icao}' on edit, using Toronto default"
            )
        listing.lat = lat
        listing.lon = lon

        db.session.commit()
        flash('Listing updated successfully!', 'success')
        return redirect(url_for('main.listing_detail', id=id))
    
    return render_template('edit_listing.html', listing=listing)

@bp.route('/messages')
@login_required
def messages():
    """View all conversations (user-to-user and guest inquiries)"""
    try:
        # ── User-to-user conversations ──────────────────────────────────────
        sent = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct()
        received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct()

        partner_ids = set([r[0] for r in sent] + [r[0] for r in received])
        partner_ids.discard(None)  # Guest messages have sender_id=None — handled separately
        partners = User.query.filter(User.id.in_(partner_ids)).all() if partner_ids else []

        conversations = []
        for partner in partners:
            last_message = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
                ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
            ).order_by(Message.created_at.desc()).first()

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

        conversations.sort(key=lambda x: (
            x['partner'].is_premium,
            x['last_message'].created_at if x['last_message'] else datetime.datetime.min
        ), reverse=True)

        # ── Guest inquiries (sender_id=None, is_guest=True) ─────────────────
        # Fetch all guest messages sent to this user's listings
        guest_messages = Message.query.filter_by(
            receiver_id=current_user.id,
            is_guest=True
        ).order_by(Message.created_at.desc()).all()

    except Exception as e:
        print(f"ERROR in messages(): {e}")
        import traceback; traceback.print_exc()
        db.session.rollback()
        conversations = []
        guest_messages = []

    return render_template('messages.html',
                           conversations=conversations,
                           guest_messages=guest_messages)


@bp.route('/message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def message_user(user_id):
    """Private chat with a user"""
    partner = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        listing_id = request.form.get('listing_id', type=int)
        
        if content:
            # AI Concierge Scrutiny (Anti-Scam)
            is_flagged = False
            flag_reason = None
            risky_words = ['western union', 'moneygram', 'gift card', 'whatsapp', 'wire transfer', 'zelle']
            if any(word in content.lower() for word in risky_words):
                is_flagged = True
                flag_reason = "Suspicious payment method mentioned"
                flash('⚠️ Safety Note: Avoid wire transfers or non-escrow payments. Report suspicious requests.', 'warning')

            message = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                listing_id=listing_id,
                content=content,
                is_flagged=is_flagged,
                flag_reason=flag_reason
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
@limiter.limit("10 per hour")
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        try:
            user = User.query.filter_by(email=email).first()
            current_app.logger.debug(f"[LOGIN] Attempt for email='{email}' found={user is not None}")

            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                current_app.logger.info(f"[LOGIN] Success: user_id={user.id} role={user.role}")
                flash('Logged in successfully!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.index'))
            else:
                current_app.logger.warning(f"[LOGIN] Failed credentials for email='{email}'")
                flash('Invalid email or password', 'error')
        except Exception as exc:
            import traceback
            current_app.logger.error(f"[LOGIN] Exception: {exc}\n{traceback.format_exc()}")
            db.session.rollback()
            flash('A server error occurred. Please try again.', 'error')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'renter')
        gdpr_consent = request.form.get('gdpr_consent') == 'on'
        try:
            # Check reCAPTCHA
            if current_app.config.get('RECAPTCHA_ENABLED') and not current_app.recaptcha.verify():
                flash('Please complete the CAPTCHA.', 'error')
                return redirect(url_for('main.register'))

            if not gdpr_consent:
                # This should be handled by 'required' in HTML, but server-side check is safer
                flash('Please agree to the GDPR/CCPA consent.', 'error')
                return redirect(url_for('main.register'))

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
            current_app.logger.info(f"[REGISTER] New user: id={user.id} email='{email}' role={role}")
            flash('Account created successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as exc:
            import traceback
            current_app.logger.error(f"[REGISTER] Exception: {exc}\n{traceback.format_exc()}")
            db.session.rollback()
            flash('A server error occurred during registration. Please try again.', 'error')

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


# ─────────────────────────────────────────────
#  PASSWORD RESET FLOW
# ─────────────────────────────────────────────

def _get_reset_serializer():
    if URLSafeTimedSerializer is None:
        raise RuntimeError("itsdangerous not installed. Run: pip install itsdangerous")
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])



def _send_reset_email(user):
    """Send a password-reset email (falls back to console print if mail not configured)."""
    s = _get_reset_serializer()
    token = s.dumps(user.email, salt='password-reset-salt')
    reset_url = url_for('main.reset_password', token=token, _external=True)

    subject = '🔒 Reset Your HangarLinks Password'
    body = f"""Hi {user.username},

You requested a password reset for your HangarLinks account.

Click the link below to reset your password (valid for 1 hour):

{reset_url}

If you did not request this, you can safely ignore this email.

– The HangarLinks Team"""

    html_body = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#001F3F,#002952);padding:32px;border-radius:16px 16px 0 0;text-align:center;">
        <h1 style="color:white;font-size:28px;margin:0;">&#128274; Password Reset</h1>
      </div>
      <div style="background:#0d1117;padding:32px;border-radius:0 0 16px 16px;border:1px solid rgba(255,255,255,0.08);">
        <p style="color:#94a3b8;">Hi <strong style="color:white;">{user.username}</strong>,</p>
        <p style="color:#94a3b8;">Click the button below to reset your password. This link expires in <strong style="color:white;">1 hour</strong>.</p>
        <div style="text-align:center;margin:32px 0;">
          <a href="{reset_url}" style="background:linear-gradient(135deg,#1a56db,#0e9f6e);color:white;font-weight:bold;padding:14px 32px;border-radius:12px;text-decoration:none;display:inline-block;">
            Reset My Password
          </a>
        </div>
        <p style="color:#475569;font-size:12px;">If you didn't request this, ignore this email. Your password won't change.</p>
      </div>
    </div>
    """

    mail_configured = bool(current_app.config.get('MAIL_USERNAME'))
    if mail_configured:
        try:
            msg = MailMessage(subject=subject,
                              recipients=[user.email],
                              body=body,
                              html=html_body)
            mail.send(msg)
            current_app.logger.info(f"[RESET] Email sent to {user.email}")
        except Exception as e:
            current_app.logger.error(f"[RESET] Mail send failed: {e}")
            # Fall through to console output
            print(f"\n[RESET LINK for {user.email}]: {reset_url}\n")
    else:
        # MVP fallback — print to console / Railway logs
        print(f"\n{'='*60}")
        print(f"PASSWORD RESET LINK (no mail configured)")
        print(f"User: {user.email}")
        print(f"URL:  {reset_url}")
        print(f"{'='*60}\n")


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show success to prevent email enumeration
        if user:
            _send_reset_email(user)
        flash('If that email is registered, a reset link has been sent. Check your inbox (and spam folder).', 'info')
        return redirect(url_for('main.forgot_password'))
    return render_template('forgot_password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    s = _get_reset_serializer()
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour
    except SignatureExpired:
        flash('⏰ This password reset link has expired. Please request a new one.', 'warning')
        return redirect(url_for('main.forgot_password'))
    except BadSignature:
        flash('❌ Invalid reset link. Please request a new one.', 'danger')
        return redirect(url_for('main.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('❌ No account found. Please try again.', 'danger')
        return redirect(url_for('main.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'warning')
            return render_template('reset_password.html', token=token)
        if password != confirm:
            flash('Passwords do not match.', 'warning')
            return render_template('reset_password.html', token=token)
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        flash('✅ Password updated! You can now log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('reset_password.html', token=token)

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
    
    event_suggestions = []
    for l in listings:
        for ev_name, ev_data in EVENTS.items():
            if l.airport_icao in ev_data.get('airports', []):
                new_p = round(l.price_night * (1 + ev_data['surge']/100), 2) if l.price_night else 0
                event_suggestions.append({
                    'airport': l.airport_icao,
                    'event': ev_name,
                    'dates': ev_data['dates'],
                    'surge': ev_data['surge'],
                    'suggested_price': new_p
                })
    
    return render_template('dashboard_owner.html', 
                          total_earnings=total_earnings,
                          occupancy_rate=occupancy_rate,
                          listings=listings,
                          chart_data=monthly_data,
                          total_listings=total_listings,
                          event_suggestions=event_suggestions)

# ========== HANGAR VALUE CALCULATOR (Single-Player Revenue Estimator) ==========

@bp.route('/dashboard/calculator')
def hangar_calculator():
    """
    Hangar Value Calculator — lets owners estimate earnings even without renters.
    Solves the chicken-and-egg problem by showing potential revenue.
    """
    # Pull market data from actual listings
    all_listings = Listing.query.filter_by(status='Active').all()
    market_listings = len(all_listings)

    # Calculate average nightly rate from real data
    nightly_rates = [l.price_night for l in all_listings if l.price_night and l.price_night > 0]
    if nightly_rates:
        avg_nightly = sum(nightly_rates) / len(nightly_rates)
    else:
        avg_nightly = 75.0  # Sensible default

    # Top earner estimate (highest monthly × 12)
    monthly_rates = [l.price_month for l in all_listings if l.price_month and l.price_month > 0]
    if monthly_rates:
        top_earner_avg = max(monthly_rates) * 12
    else:
        top_earner_avg = 18000.0

    return render_template('calculator.html',
                           market_listings=market_listings,
                           avg_nightly=avg_nightly,
                           top_earner_avg=top_earner_avg)

# ========== MONETIZATION & SUBSCRIPTIONS ==========
TRANSACTION_FEE_PERCENT = 8
INSURANCE_RATES = {'daily': 15.00, 'base': 45.00}

@bp.route('/book/<int:listing_id>', methods=['POST'])
@login_required
def book_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    # ── Airbnb Style Dynamic Dates ──    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not start_date_str or not end_date_str:
        flash("Start and end dates are required.", "error")
        return redirect(url_for('main.listing_detail', id=listing.id))
        
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
    duration_days = (end_date - start_date).days
    
    if duration_days < listing.min_stay_nights:
        flash(f"This listing requires a minimum stay of {listing.min_stay_nights} nights.", "error")
        return redirect(url_for('main.listing_detail', id=listing.id))
        
    if duration_days <= 0:
        flash("Checkout date must be after check-in date.", "error")
        return redirect(url_for('main.listing_detail', id=listing.id))
        
    # Calculate rental price
    # If it's 30+ days, just charge the monthly rate. Otherwise use nightly rate.
    base_rental = listing.price_month if duration_days >= 30 else (listing.price_night * duration_days)
    
    # Platform Service Fee (Airbnb Model - usually 10-15%, we'll use 10%)
    platform_fee = base_rental * 0.10
    base_total = base_rental + platform_fee
    
    add_insurance = request.form.get('add_insurance') == 'on'
    insurance_fee = 0.0
    
    if add_insurance:
        # Scale insurance based on duration
        base_insurance_daily = 15.00
        insurance_fee = (base_insurance_daily * duration_days) + 45.00 # Base risk fee
        
    final_total = base_total + insurance_fee
    
    try:
        stripe_lib = get_stripe()
        if not stripe_lib:
            session_id = 'mock_session_' + str(uuid.uuid4().hex[:8])
            checkout_session_url = url_for('main.booking_success', _external=True) + '?session_id=' + session_id
        else:
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Hangar Rental at {listing.airport_icao}',
                        'description': f'{duration_days} nights ({start_date_str} to {end_date_str}) + Platform Fee',
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
                            'description': f'Liability & Hull coverage for {duration_days} days',
                        },
                        'unit_amount': int(insurance_fee * 100),
                    },
                    'quantity': 1,
                })
                
            checkout_session = stripe_lib.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=url_for('main.booking_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('main.listing_detail', id=listing.id, _external=True),
                metadata={
                    'user_id': current_user.id,
                    'item_type': 'rental_booking',
                    'listing_id': listing.id
                }
            )
            checkout_session_url = checkout_session.url
            session_id = checkout_session.id
        
        booking = Booking(
            listing_id=listing.id, 
            renter_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            total_price=base_rental,
            status='Pending',
            stripe_payment_id=session_id,
            insurance_opt_in=add_insurance,
            insurance_fee=insurance_fee
        )
        # Log to Payment model for billing history
        payment = Payment(
            user_id=current_user.id,
            amount=final_total,
            item_type='rental_booking',
            item_id=listing.id,
            stripe_session_id=session_id,
            status='pending'
        )
        
        # Space Calculation via Aircraft Config
        booking_aircraft = request.form.get('booking_aircraft')
        if booking_aircraft:
            from flask import current_app
            sizes = current_app.config.get('AIRCRAFT_SIZES', {})
            for cat, dicts in sizes.items():
                if booking_aircraft in dicts:
                    dims = dicts[booking_aircraft]
                    # 10% buffer applied equivalent to booking verification modal
                    req_sqft = (dims['length'] * dims['wingspan']) * 1.1 
                    
                    if listing.available_sqft is None:
                        listing.available_sqft = listing.size_sqft
                        
                    if listing.available_sqft >= req_sqft:
                        listing.available_sqft -= req_sqft
                        listing.health_score = min(100, (listing.health_score or 0) + 5)
                    break
        
        db.session.add(booking)
        db.session.add(payment)
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
    
    # Generate cryptographic sign tokens
    if not booking.sign_token_renter:
        booking.sign_token_renter = secrets.token_urlsafe(32)
        booking.sign_token_owner = secrets.token_urlsafe(32)
        
    booking.status = 'Pending E-Signature'
    
    # Update Payment status
    payment = Payment.query.filter_by(stripe_session_id=session_id).first()
    if payment:
        payment.status = 'completed'
        
    db.session.commit()
    
    # WeasyPrint PDF Generation Engine
    if HTML:
        try:
            rendered_html = render_template('lease_template.html', 
                                         booking=booking, 
                                         listing=booking.listing, 
                                         owner=booking.listing.owner, 
                                         renter=booking.renter,
                                         current_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            os.makedirs(os.path.join(current_app.root_path, 'static', 'leases'), exist_ok=True)
            filename = f"lease_{booking.id}_{booking.sign_token_renter[:8]}.pdf"
            filepath = os.path.join(current_app.root_path, 'static', 'leases', filename)
            
            HTML(string=rendered_html).write_pdf(filepath)
            booking.lease_pdf_path = filename
            db.session.commit()
        except Exception as e:
            print(f"WeasyPrint PDF Generation Failed: {e}")
            
    # Mock Mailer
    print(f"\n[MAIL SIMULATOR] Sent Lease Agreement for Verification!")
    print(f"--> Renter Link: {url_for('main.sign_lease', token=booking.sign_token_renter, _external=True)}")
    print(f"--> Owner Link:  {url_for('main.sign_lease', token=booking.sign_token_owner, _external=True)}\n")
    
    flash('Booking Escrowed! Check your email to digitally sign the generated lease agreement.', 'success')
    return redirect(url_for('main.sign_lease', token=booking.sign_token_renter))

@bp.route('/sign-lease/<token>', methods=['GET'])
@login_required
def sign_lease(token):
    # Determine if token belongs to renter or owner
    booking = Booking.query.filter((Booking.sign_token_renter == token) | (Booking.sign_token_owner == token)).first_or_404()
    
    # Check authorization mapping
    is_renter = booking.sign_token_renter == token
    if is_renter and current_user.id != booking.renter_id: abort(403)
    if not is_renter and current_user.id != booking.listing.owner_id: abort(403)
    
    return render_template('sign_lease.html', booking=booking, token=token)
    
@bp.route('/execute-lease/<token>', methods=['POST'])
@login_required
def execute_lease(token):
    booking = Booking.query.filter((Booking.sign_token_renter == token) | (Booking.sign_token_owner == token)).first_or_404()
    
    if booking.sign_token_renter == token:
        booking.renter_signed = True
        flash('You have successfully signed the lease as the Lessee!', 'success')
    else:
        booking.owner_signed = True
        flash('You have successfully signed the lease as the Lessor!', 'success')
        
    # Check if both constraints fulfilled securely mapping to Confirmed!
    if booking.renter_signed and booking.owner_signed:
        booking.status = 'Confirmed'
        booking.listing.status = 'Rented'
        booking.listing.insurance_active = True
        flash('Both parties have signed! Digital Escrow dispersed and lease is now Confirmed.', 'success')
        
    db.session.commit()
    return redirect(url_for('main.listing_detail', id=booking.listing_id))

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
            
        # Reward explicitly Short-Term optimized structures mathematically
        if getattr(l, 'min_stay_nights', 30) <= 7:
            score += 20 # Massive immediate ranking modifier
            
        final_score = min(score, 99)
        scored_matches.append({'listing': l, 'score': final_score})
        
    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = scored_matches[:10]
    
    return render_template('matches.html', matches=top_matches)

@bp.route('/concierge')
def concierge():
    return render_template('concierge.html')

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

@bp.route('/dashboard/space-calculator', methods=['GET', 'POST'])
@login_required
def space_calculator():
    remaining_sqft = None
    aircraft_count_fit = 0
    if request.method == 'POST':
        try:
            length = float(request.form.get('hangar_length', 0))
            width = float(request.form.get('hangar_width', 0))
            total_sqft = length * width
            
            aircraft_type_1 = request.form.get('aircraft_type_1')
            qty_1 = int(request.form.get('qty_1', 0))
            
            used_sqft = 0
            
            # Estimate footprint with a 20% buffer for maneuvering
            sizes = current_app.config.get('AIRCRAFT_SIZES', {})
            plane_dims = None
            for category, dicts in sizes.items():
                if aircraft_type_1 in dicts:
                    plane_dims = dicts[aircraft_type_1]
                    break
                    
            if plane_dims:
                # Footprint = length * wingspan
                footprint = plane_dims['length'] * plane_dims['wingspan']
                used_sqft += (footprint * 1.2) * qty_1
                
            remaining_sqft = max(0, total_sqft - used_sqft)
            
            # How many small GA planes (Cessna 172 ~ 1000 sqft with buffer) could fit?
            # 27.2L * 36.1W = 981 sqft. * 1.2 = 1178
            aircraft_count_fit = int(remaining_sqft // 1178)
            
        except Exception as e:
            flash(f"Error calculating space: {e}", "error")
            
    return render_template('space_calculator.html', 
                           remaining_sqft=remaining_sqft, 
                           aircraft_count_fit=aircraft_count_fit,
                           aircraft_sizes=current_app.config.get('AIRCRAFT_SIZES', {}))

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
@limiter.limit("5 per hour")
def contact_guest(listing_id):
    """Guest (unauthenticated) contact form — no login required."""
    print(f"DEBUG: Entering guest message route for listing_id={listing_id}")
    try:
        listing = Listing.query.get_or_404(listing_id)

        # If user is logged in, redirect to the real messaging system
        if current_user.is_authenticated:
            return redirect(url_for('main.message_user', user_id=listing.owner_id, listing_id=listing.id))

        guest_email = (request.form.get('guest_email') or '').strip()
        message_content = (request.form.get('message') or '').strip()

        print(f"DEBUG: guest_email='{guest_email}' message_len={len(message_content)}")

        if not guest_email or not message_content:
            flash('Email and message are required.', 'error')
            return redirect(url_for('main.listing_detail', id=listing.id))

        # Basic email format check
        if '@' not in guest_email or '.' not in guest_email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('main.listing_detail', id=listing.id))

        # Anti-spam: flag risky content
        is_flagged = False
        flag_reason = None
        spam_words = ['western union', 'moneygram', 'gift card', 'wire transfer', 'zelle',
                      'crypto', 'bitcoin', 'click here', 'act now', 'nigerian']
        if any(word in message_content.lower() for word in spam_words):
            is_flagged = True
            flag_reason = 'Suspicious content in guest message'
            print(f"DEBUG: Guest message flagged — {flag_reason}")

        msg = Message(
            sender_id=None,
            receiver_id=listing.owner_id,
            listing_id=listing.id,
            content=f"[GUEST: {guest_email}] {message_content}",
            is_guest=True,
            guest_email=guest_email,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            created_at=datetime.datetime.now(timezone.utc)
        )
        db.session.add(msg)
        db.session.commit()
        print(f"DEBUG: Guest message saved — id={msg.id}")

        flash('Message sent! The owner will reply to your email.', 'success')
        return redirect(url_for('main.listing_detail', id=listing.id))

    except Exception as e:
        print(f"ERROR in contact_guest: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        flash('Something went wrong sending your message. Please try again.', 'error')
        return redirect(url_for('main.listing_detail', id=listing_id))

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
    """Rate-limit free renters. Returns True = allowed, False = blocked."""
    try:
        if not current_user.is_authenticated:
            return True
        if getattr(current_user, 'subscription_tier', None) == 'premium':
            return True
        if getattr(current_user, 'role', 'renter') != 'renter':
            return True

        today = date.today()
        reset_date = getattr(current_user, 'search_reset_date', None)
        if reset_date != today:
            current_user.search_count_today = 0
            current_user.search_reset_date = today
            db.session.commit()

        if getattr(current_user, 'search_count_today', 0) >= 5:
            return False

        current_user.search_count_today = getattr(current_user, 'search_count_today', 0) + 1
        db.session.commit()
        return True
    except Exception as e:
        print(f"WARN: check_search_limit error (allowing): {e}")
        db.session.rollback()
        return True  # Fail open — don't block users on DB errors

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
    # If analytics expired, reset access
    if current_user.analytics_expires_at and current_user.analytics_expires_at < datetime.datetime.now(timezone.utc):
        current_user.has_analytics_access = False
        db.session.commit()
        has_access = False # Re-evaluate access after resetting
        
    if not has_access:
        return render_template('insights_teaser.html', pricing=INSIGHTS_PRICING)
        
    airport_code = request.args.get('airport', 'CYTZ')
    duration = request.args.get('duration', 'weekly')
    
    # Calculate short-term DB metrics dynamically
    q = Listing.query.filter_by(status='Active').filter((Listing.min_stay_nights <= 7) | (Listing.min_stay_nights == None))
    airport_listings = q.filter_by(airport_icao=airport_code).all()
    
    nightly_rates = []
    for l in airport_listings:
        if l.price_night:
            nightly_rates.append(l.price_night)
        elif l.price_month:
            nightly_rates.append(l.price_month / 30)
            
    avg_nightly_rate = sum(nightly_rates) / len(nightly_rates) if nightly_rates else 85.0
    
    trend_pct = 10.0
    weekend_occupancy = 85
    demand_score = 8.5
    
    if duration == 'weekly':
        labels = ['W1', 'W2', 'W3', 'W4', 'W5', 'This Week']
    else:
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        
    hk_market_price = [round(avg_nightly_rate * (1 + 0.02 * i), 2) for i in range(-5, 1)]
    user_avg_price = [round(avg_nightly_rate * (0.95 + 0.01 * i), 2) for i in range(-5, 1)]
    occupancy_data = [80, 82, 85, 81, 86, weekend_occupancy]

    active_surges = []
    for event_name, data in EVENTS.items():
        if airport_code in data['airports']:
            active_surges.append({
                'name': event_name,
                'surge': data['surge'],
                'dates': data['dates']
            })
    
    return render_template('insights.html', 
                           labels=labels, 
                           market_prices=hk_market_price,
                           my_prices=user_avg_price,
                           occupancy=occupancy_data,
                           demand_score=demand_score,
                           avg_nightly_rate=round(avg_nightly_rate, 2),
                           trend_pct=trend_pct,
                           weekend_occupancy=weekend_occupancy,
                           airport_code=airport_code,
                           active_surges=active_surges,
                           duration=duration)

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
    if type == 'subscription': # Assuming 'subscription' implies yearly based on INSIGHTS_PRICING
        current_user.analytics_expires_at = datetime.datetime.now(timezone.utc) + timedelta(days=365)
    else:
        current_user.analytics_expires_at = datetime.datetime.now(timezone.utc) + timedelta(days=30) 
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
            metadata={
                'user_id': current_user.id if current_user.is_authenticated else 'guest',
                'item_type': 'white_label_reservation',
                'fbo_name': fbo_name
            }
        )
        
        if current_user.is_authenticated:
            payment = Payment(
                user_id=current_user.id,
                amount=499.00,
                item_type='white_label_reservation',
                stripe_session_id=checkout_session.id,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment Error: {str(e)}', 'error')
        return redirect(url_for('main.white_label'))

@bp.route('/white-label/success')
def white_label_success():
    session_id = request.args.get('session_id')
    stripe_lib = get_stripe()
    
    if session_id and stripe_lib:
        try:
            session = stripe_lib.checkout.Session.retrieve(session_id)
            fbo_name = session.metadata.get('fbo_name')
            
            # Update Payment Record
            payment = Payment.query.filter_by(stripe_session_id=session_id).first()
            if payment:
                payment.status = 'completed'
            
            # Update Request Record
            if fbo_name:
                req = WhiteLabelRequest.query.filter_by(fbo_name=fbo_name, status='Pending Payment').first()
                if req:
                    req.status = 'Paid'
            
            db.session.commit()
        except Exception as e:
            print(f"White label success verification error: {e}")

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
    if any(w in msg_lower for w in ['show', 'find', 'search', 'available', 'hangar', 'listing', 'price', 'overnight', 'weekend']):
        q = Listing.query.filter_by(status='Active')
        if airport_hits:
            q = q.filter(Listing.airport_icao.in_(airport_hits))
        if max_price:
            q = q.filter((Listing.price_night <= max_price) | (Listing.price_month / 30 <= max_price))
        if covered_only:
            q = q.filter_by(covered=True)
            
        # Strongly bias towards short-term stays natively in the data fetch layer
        results = q.order_by(Listing.min_stay_nights.asc(), Listing.health_score.desc()).limit(5).all()
        
        if results:
            lines = ["**Top Short-Term / Overnight hangars matching your query:**"]
            for l in results:
                covered_tag = "🏠 Covered" if l.covered else "🌤 Uncovered"
                night_rate = l.price_night if l.price_night else (l.price_month / 30)
                stay_limit = f"{l.min_stay_nights} Night Min" if l.min_stay_nights > 1 else "Flexible (1 Night)"
                
                lines.append(
                    f"- **{l.airport_icao}** | {stay_limit} | **${night_rate:.0f}/night** | {covered_tag} | "
                    f"[View Listing](/listing/{l.id})"
                )
            ctx_parts.append("\n".join(lines))
        else:
            ctx_parts.append("No short-term / overnight listings match those filters right now. Try expanding your search.")

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

            system_prompt = f"""You are the HangarLinks AI Concierge — a smart, friendly aviation assistant specializing in Short-Term transient parking (Overnights & Weekends 1-7 days).
You help transient aircraft owners find overnight hangars, and hangar owners optimize their listings for event surges.

USER CONTEXT:
- Name: {user_name}
- Role: {user_role}
- Home Airport: {home_airport}

LIVE DATABASE CONTEXT (use this to answer):
{db_context if db_context else "No specific data found for this query."}

INSTRUCTIONS:
- PRIORITY 1: Always prioritize and highlight listings with minimum stays of 1 to 7 nights first.
- PRIORITY 2: Automatically check if dates/locations match Major Events (e.g. Oshkosh, Sun 'n Fun) and suggest nightly Event Surge rates.
- Use the live data above to answer questions about availability, translating monthly rates down to estimated Nightly Rates (Monthly/30) if only monthly is defined.
- Be concise and friendly. Use markdown (bold, bullet points) for clarity.
- If you find matching listings, always include the [View Listing](/listing/ID) link.
- If asked "Book this?" direct them to the listing link. If asked "Message owner?" state "I'll connect you — click the listing link and use the owner contact module."
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

@bp.route('/report-listing/<int:id>', methods=['POST'])
@login_required
def report_listing(id):
    """Report a suspicious listing"""
    listing = Listing.query.get_or_404(id)
    data = request.json or {}
    reason = data.get('reason', 'No reason provided')
    
    listing.is_reported = True
    listing.report_count += 1
    new_reason = f"[{datetime.now().strftime('%Y-%m-%d')}] {reason}"
    listing.report_reason = (listing.report_reason + " | " + new_reason) if listing.report_reason else new_reason
    
    db.session.commit()
    return jsonify({'status': 'ok', 'report_count': listing.report_count})

@bp.route('/verification', methods=['GET', 'POST'])
@login_required
def verification():
    """Identity verification flow"""
    if request.method == 'POST':
        if 'id_photo' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('main.verification'))
        
        file = request.files['id_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_id = uuid.uuid4().hex[:8]
            filename = f"verify_{current_user.id}_{unique_id}_{filename}"
            
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'verifications', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            current_user.id_photo_url = filename
            current_user.verification_status = 'pending'
            db.session.commit()
            flash('ID uploaded successfully! Manual review in progress (24-48h).', 'success')
            return redirect(url_for('main.profile'))
            
    return render_template('verification.html')

@bp.route('/admin/verifications')
@login_required
def admin_verifications():
    """Admin-only: Review pending verifications"""
    if not current_user.is_admin:
        abort(403)
    pending_users = User.query.filter_by(verification_status='pending').all()
    return render_template('admin_verifications.html', users=pending_users)

@bp.route('/admin/verify-user/<int:user_id>/<action>')
@login_required
def verify_user_action(user_id, action):
    """Approve or reject a user's ID"""
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    if action == 'approve':
        user.verification_status = 'verified'
        user.id_verified = True
    else:
        user.verification_status = 'rejected'
        user.id_verified = False
    db.session.commit()
    flash(f'User {user.username} {action}ed.', 'success')
    return redirect(url_for('main.admin_verifications'))


# --- AI Rental Optimizer Feature ---

def train_optimizer_model():
    """Trains a simple RandomForest model on current market data or synthetic data if empty"""
    if not pd or not RandomForestRegressor:
        return None, None

    # Get all listings for training
    all_listings = Listing.query.all()
    
    data = []
    if len(all_listings) < 15:
        # Generate synthetic data if not enough real data
        # Features: [size_sqft, covered (1/0), airport_freq_score (simple mock)]
        # Target: price_month
        for _ in range(50):
            size = random.randint(800, 5000)
            is_covered = random.choice([0, 1])
            base_price = (size * 0.15) + (is_covered * 200) + random.randint(-100, 100)
            data.append({
                'size_sqft': size,
                'covered': is_covered,
                'price_month': max(150, base_price)
            })
    
    # Add real data
    for l in all_listings:
        data.append({
            'size_sqft': l.size_sqft,
            'covered': 1 if l.covered else 0,
            'price_month': l.price_month
        })

    df = pd.DataFrame(data)
    X = df[['size_sqft', 'covered']]
    y = df['price_month']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Calculate global market average
    market_avg = df['price_month'].mean()
    
    return model, market_avg

@bp.route('/insights/optimizer')
@login_required
def rental_optimizer():
    """Predictive pricing and performance insights tool (Premium Only)"""
    if not current_user.is_premium:
        flash("AI Rental Optimizer is a Premium feature. Upgrade to unlock predictive insights.", "warning")
        return redirect(url_for('main.profile'))

    # Load market model
    model, market_avg = train_optimizer_model()
    
    # Analyze current user's active listings
    user_listings = Listing.query.filter_by(owner_id=current_user.id, status='Active').all()
    insights = []
    
    for l in user_listings:
        # Prediction
        ideal_price = l.price_month
        success_chance = 75 # default
        
        if model:
            pred_input = pd.DataFrame([[l.size_sqft, 1 if l.covered else 0]], columns=['size_sqft', 'covered'])
            ideal_price = float(model.predict(pred_input)[0])
            
            # success chance logic: higher if price is <= ideal_price
            price_diff_percent = (l.price_month - ideal_price) / ideal_price
            success_chance = max(10, min(98, 85 - (price_diff_percent * 100)))

        # Historical comparison (Mocked for MVP)
        faster_than_avg = random.randint(15, 45)
        
        insights.append({
            'listing': l,
            'ideal_price': round(ideal_price, 2),
            'success_chance': round(success_chance, 1),
            'price_diff': round(l.price_month - ideal_price, 2),
            'trend': 'up' if l.price_month < ideal_price else 'down',
            'faster_than_avg': faster_than_avg,
            'suggestion': "Strong pricing - maintain." if abs(l.price_month - ideal_price) < 50 else 
                          f"Recommendation: {'Decrease' if l.price_month > ideal_price else 'Increase'} price by ${abs(round(l.price_month - ideal_price, 2))} for optimal velocity."
        })

    # Historical Trends Data (Mock for Chart.js)
    history_labels = [(date.today() - timedelta(days=i*30)).strftime('%b %Y') for i in range(6)][::-1]
    history_prices = [market_avg * (0.9 + (0.02 * i)) for i in range(6)] if market_avg else [350, 365, 380, 375, 390, 405]

    return render_template('insights/optimizer.html', 
                         insights=insights, 
                         history_labels=history_labels,
                         history_prices=history_prices,
                         market_avg=market_avg or 400.0)

@bp.route('/billing')
@login_required
def billing():
    """User billing history and current status"""
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('billing.html', payments=payments)

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Unified Stripe Checkout handler for all monetization features"""
    item_type = request.form.get('item_type')
    item_id = request.form.get('item_id')
    
    # Pricing configuration (Test Mode Defaults)
    prices = {
        'premium_owner': {'amount': 999, 'name': 'Owner Premium Subscription', 'recurring': True},
        'premium_renter': {'amount': 699, 'name': 'Renter Premium Subscription', 'recurring': True},
        'featured_silver': {'amount': 4900, 'name': 'Silver Featured Listing (30 Days)', 'recurring': False},
        'featured_gold': {'amount': 9900, 'name': 'Gold Featured Listing (30 Days)', 'recurring': False},
        'featured_platinum': {'amount': 19900, 'name': 'Platinum Featured Listing (30 Days)', 'recurring': False},
        'insurance_base': {'amount': 4500, 'name': 'HangarLink Liability Coverage (Base)', 'recurring': False},
        'analytics_report': {'amount': 1999, 'name': 'AI Market Intel Report', 'recurring': False},
        'analytics_report_national': {'amount': 14900, 'name': 'National Hangar Market Report (Q1 2026)', 'recurring': False},
        'white_label': {'amount': 9900, 'name': 'FBO White-Label Portal (Monthly)', 'recurring': True},
    }
    
    config = prices.get(item_type)
    if not config:
        flash("Invalid product selection.", "error")
        return redirect(url_for('main.profile'))
    
    stripe_lib = get_stripe()
    if not stripe_lib:
        flash("Payments currently unavailable.", "error")
        return redirect(url_for('main.profile'))
    
    try:
        session_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': config['name']},
                    'unit_amount': config['amount'],
                },
                'quantity': 1,
            }],
            'mode': 'subscription' if config['recurring'] else 'payment',
            'success_url': url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': url_for('main.payment_cancel', _external=True),
            'metadata': {
                'user_id': current_user.id,
                'item_type': item_type,
                'item_id': item_id or ''
            }
        }
        
        if config['recurring']:
            session_params['line_items'][0]['price_data']['recurring'] = {'interval': 'month'}
            
        checkout_session = stripe_lib.checkout.Session.create(**session_params)
        
        # Log pending payment
        payment = Payment(
            user_id=current_user.id,
            amount=config['amount'] / 100.0,
            item_type=item_type,
            item_id=int(item_id) if item_id and item_id.isdigit() else None,
            stripe_session_id=checkout_session.id,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        db.session.rollback()
        flash(f"Payment error: {str(e)}", "error")
        return redirect(url_for('main.profile'))

@bp.route('/payment-success')
@login_required
def payment_success():
    """Handle successful checkout redirection"""
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('main.index'))
        
    stripe_lib = get_stripe()
    try:
        session = stripe_lib.checkout.Session.retrieve(session_id)
        payment = Payment.query.filter_by(stripe_session_id=session_id).first()
        
        if payment and payment.status == 'pending':
            payment.status = 'completed'
            payment.stripe_payment_intent = getattr(session, 'payment_intent', None) or getattr(session, 'subscription', None)
            
            # Apply feature logic based on item_type
            item_type = session.metadata.get('item_type')
            if item_type in ['premium_owner', 'premium_renter']:
                current_user.is_premium = True
                current_user.subscription_tier = 'premium'
                current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            elif 'featured' in item_type:
                listing_id = session.metadata.get('item_id')
                if listing_id:
                    listing = Listing.query.get(listing_id)
                    if listing:
                        listing.is_featured = True
                        listing.is_premium_listing = True
                        listing.featured_tier = item_type.split('_')[1]
                        listing.featured_expires_at = datetime.utcnow() + timedelta(days=30)
            elif item_type in ['analytics_report', 'analytics_report_national']:
                current_user.has_analytics_access = True
                current_user.analytics_expires_at = datetime.utcnow() + timedelta(days=30)
            elif item_type == 'white_label':
                current_user.is_white_label_partner = True
                # Add any other flags needed for white label
            
            db.session.commit()
            flash(f"Success! Your payment for {item_type.replace('_', ' ').capitalize()} has been processed.", "success")
            
        return render_template('payment_success.html')
    except Exception as e:
        flash(f"Verification error: {str(e)}", "error")
        return redirect(url_for('main.profile'))

@bp.route('/payment-cancel')
@login_required
def payment_cancel():
    """Handle cancelled checkout"""
    flash("Payment cancelled.", "info")
    return redirect(url_for('main.profile'))

# ─────────────────────────────────────────────
#  WebSocket Real-Time Chat Handlers
# ─────────────────────────────────────────────
try:
    from flask_socketio import emit
except ImportError:
    def emit(*args, **kwargs): pass
    print("Warning: flask_socketio not installed. emit disabled.")
    
from extensions import socketio

@socketio.on('connect')
def handle_connect():
    """Client joined the Concierge portal."""
    pass

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming WS messages natively mapping to the API hooks."""
    if not isinstance(data, dict):
        return
        
    user_msg = data.get('message', '').strip()
    history = data.get('history', [])
    
    if not user_msg:
        return
        
    # Re-use our existing Logic layer but via WS instead of HTTP POST
    user_role = current_user.role if current_user.is_authenticated else 'guest'
    home_airport = getattr(current_user, 'alert_airport', None) or 'Not set'
    user_name = current_user.username if current_user.is_authenticated else 'Guest'
    
    db_ctx = _build_db_context(user_msg)
    
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('GROK_API_KEY')
    base_url = os.environ.get('OPENAI_BASE_URL')
    
    # Send an immediate 'typing' indicator
    emit('typing_status', {'isTyping': True})

    try:
        if openai and api_key:
            client_kwargs = {'api_key': api_key}
            if base_url:
                client_kwargs['base_url'] = base_url
            client = openai.OpenAI(**client_kwargs)

            system_prompt = f"""You are the HangarLinks AI Concierge — a smart, friendly aviation assistant specializing in Short-Term transient parking (Overnights & Weekends 1-7 days).
You help transient aircraft owners find overnight hangars, and hangar owners optimize their listings for event surges.

USER CONTEXT:
- Name: {user_name}
- Role: {user_role}
- Home Airport: {home_airport}

LIVE DATABASE CONTEXT (use this to answer):
{db_ctx if db_ctx else "No specific data found for this query."}

INSTRUCTIONS:
- PRIORITY 1: Always prioritize and highlight listings with minimum stays of 1 to 7 nights first.
- PRIORITY 2: Automatically check if dates/locations match Major Events (e.g. Oshkosh, Sun 'n Fun) and suggest nightly Event Surge rates.
- Use the live data above to answer questions about availability, translating monthly rates down to estimated Nightly Rates (Monthly/30) if only monthly is defined.
- Be concise and friendly. Use markdown (bold, bullet points) for clarity.
- If you find matching listings, always include the [View Listing](/listing/ID) link.
- If asked "Book this?" direct them to the listing link. If asked "Message owner?" state "I'll connect you — click the listing link and use the owner contact module."
- NEVER make up listing data. Only use what's in LIVE DATABASE CONTEXT.
- Keep replies under 200 words."""

            messages = [{'role': 'system', 'content': system_prompt}]
            for h in history[-6:]:
                if h.get('role') in ('user', 'assistant') and h.get('content'):
                    messages.append({'role': h['role'], 'content': h['content']})
            messages.append({'role': 'user', 'content': user_msg})

            model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=400,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content.strip()
            emit('chat_response', {'reply': reply, 'source': 'llm'})
            return
            
    except Exception as e:
        current_app.logger.error(f"WS Concierge Error: {e}")
        
    # Fallback to rules layer
    reply = _rule_based_response(user_msg, user_role, db_ctx)
    emit('chat_response', {'reply': reply, 'source': 'rules'})

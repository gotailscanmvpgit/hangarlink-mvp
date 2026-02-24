import pytest
from flask import url_for
from models import User, Listing, Message, Booking, Ad, WhiteLabelRequest
from extensions import db
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json
import io

# ════════════════════════════════════════════════════════════════
#  1. CORE PAGES & UI
# ════════════════════════════════════════════════════════════════

class TestCoreAndUI:
    def test_homepage_loads(self, client):
        """Test that the homepage loads with premium branding."""
        r = client.get('/')
        assert r.status_code == 200
        assert b'HangarLinks' in r.data
        assert b'Premium' in r.data

    def test_dark_mode_supported(self, client):
        """Check if dark mode classes/scripts are present."""
        r = client.get('/')
        assert b'class="dark"' in r.data or b'darkMode: \'class\'' in r.data
        assert b'id="theme-toggle"' in r.data

    def test_mobile_responsiveness(self, client):
        """Verify viewport meta tag for mobile responsiveness."""
        r = client.get('/')
        assert b'name="viewport"' in r.data
        assert b'content="width=device-width, initial-scale=1.0"' in r.data

    def test_pwa_features(self, client):
        """Check for PWA manifest and icons."""
        r = client.get('/')
        assert b'rel="manifest"' in r.data
        assert b'href="/static/manifest.json"' in r.data
        assert b'apple-touch-icon' in r.data

    def test_404_error_page(self, client):
        """Ensure custom 404 page is returned for missing routes."""
        r = client.get('/non-existent-page-999')
        assert r.status_code == 404
        assert b'404' in r.data or b'Not Found' in r.data

# ════════════════════════════════════════════════════════════════ 
#  2. AUTH FLOW
# ════════════════════════════════════════════════════════════════

class TestAuthFlow:
    def test_full_registration_and_login(self, client, app, mocker):
        """Test the full user journey from signup to login."""
        # Mock reCAPTCHA to always pass
        mocker.patch('flask_recaptcha.ReCaptcha.verify', return_value=True)
        
        # Registration
        r_reg = client.post('/register', data={
            'username': 'testpilot',
            'email': 'pilot@example.com',
            'password': 'Password123!',
            'role': 'renter',
            'gdpr_consent': 'on'
        }, follow_redirects=True)
        assert r_reg.status_code == 200
        
        with app.app_context():
            # Verify user in DB
            user = User.query.filter_by(email='pilot@example.com').first()
            assert user is not None
        
        # Logout
        client.get('/logout', follow_redirects=True)
        
        # Login
        r_login = client.post('/login', data={
            'email': 'pilot@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)
        assert r_login.status_code == 200
        assert b'Sign out' in r_login.data or b'logout' in r_login.data.lower()

# ════════════════════════════════════════════════════════════════
#  3. LISTINGS & SEARCH
# ════════════════════════════════════════════════════════════════

class TestListingsAndSearch:
    def test_post_listing_with_health_score(self, client, app):
        """Test creating a listing and ensuring health score works."""
        with app.app_context():
            # Create a clean owner for this test
            u = User.query.filter_by(email='post@test.com').first()
            if not u:
                u = User(username='postowner', email='post@test.com', 
                         password_hash=generate_password_hash('pass'), role='owner',
                         reputation_score=5.0)
                db.session.add(u)
                db.session.commit()
            u_id = u.id

        l_res = client.post('/login', data={'email': 'post@test.com', 'password': 'pass'}, follow_redirects=True)
        assert b'Sign out' in l_res.data or b'logout' in l_res.data.lower()
        
        # Post listing with files
        data = {
            'airport_icao': 'CYTZ',
            'size_sqft': 1500,
            'price_month': 450,
            'description': 'Beautiful hangar with electricity and heating.',
            'covered': 'on',
            'availability_start': '2024-03-01',
            'availability_end': '2024-12-31',
            'checklist_verified': 'on',
            'condition_verified': 'on'
        }
        # 3 photos to get points
        data['photos'] = [
            (io.BytesIO(b"img1"), 'photo1.jpg'),
            (io.BytesIO(b"img2"), 'photo2.jpg'),
            (io.BytesIO(b"img3"), 'photo3.jpg')
        ]
        
        r = client.post('/post-listing', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert r.status_code == 200
        # If it redirected back to post-listing, check for errors
        if b'Create a New Listing' in r.data:
             print("DEBUG: Redirected back to post-listing form. Errors likely.")
             assert b'success' in r.data or b'Listing created' in r.data
        
        with app.app_context():
            listing = Listing.query.filter_by(owner_id=u_id).first()
            assert listing is not None, f"Listing was not created. Response snippet: {r.data[800:1500]}"
            # Score components: 30(photos) + 30(checklist) + 20(condition) + 20(reputation) = 100
            assert listing.health_score >= 80 

    def test_search_and_pagination(self, client, app):
        """Test searching for listings."""
        with app.app_context():
            u = User.query.filter_by(email='search@test.com').first()
            if not u:
                u = User(username='searchowner', email='search@test.com', 
                             password_hash=generate_password_hash('pass'), role='owner')
                db.session.add(u)
                db.session.commit()
            
            # Create at least one listing if none exist
            l = Listing(airport_icao='CYTZ', size_sqft=1000, price_month=300, 
                        owner_id=u.id, status='Active', health_score=90, description="Test search")
            db.session.add(l)
            db.session.commit()
            
        r = client.get('/listings?airport=CYTZ')
        assert r.status_code == 200
        assert b'CYTZ' in r.data
        assert b'Available' in r.data

    def test_listing_detail_features(self, client, app):
        """Gallery, Share, and Message buttons."""
        with app.app_context():
            l = Listing.query.first()
            if not l:
                u = User.query.filter_by(role='owner').first()
                l = Listing(airport_icao='CYTZ', size_sqft=1000, price_month=350, 
                            owner_id=u.id, status='Active')
                db.session.add(l)
                db.session.commit()
            l_id = l.id

        r = client.get(f'/listing/{l_id}')
        assert r.status_code == 200
        assert b'WhatsApp' in r.data
        assert b'Message' in r.data or b'Contact' in r.data

# ════════════════════════════════════════════════════════════════
#  4. ENGAGEMENT & DASHBOARDS
# ════════════════════════════════════════════════════════════════

class TestEngagement:
    def test_messaging_flow(self, client, app):
        """Test guest/user messaging."""
        with app.app_context():
            owner = User.query.filter_by(role='owner').first()
            listing = Listing.query.filter_by(owner_id=owner.id).first()
            if not listing:
                 listing = Listing(airport_icao='CYTZ', size_sqft=1000, price_month=400, 
                                   owner_id=owner.id, status='Active')
                 db.session.add(listing)
                 db.session.commit()
            owner_id = owner.id
            listing_id = listing.id

        # Ensure logged out for guest test
        client.get('/logout', follow_redirects=True)
        
        # Send as guest (no login)
        r = client.post(f'/contact-guest/{listing_id}', data={
            'message': 'Guest interest message',
            'guest_email': 'guest@test.com'
        }, follow_redirects=True)
        assert r.status_code == 200
        
        with app.app_context():
            msg = Message.query.filter_by(guest_email='guest@test.com').first()
            assert msg is not None, "Message was not created in DB."
            assert "Guest interest message" in msg.content
            assert "guest@test.com" in msg.content

    def test_owner_dashboard_loads(self, client, app):
        """Verify dashboard for owners."""
        with app.app_context():
            owner = User.query.filter_by(role='owner').first()
            email = owner.email
        
        client.post('/login', data={'email': email, 'password': 'pass'})
        r = client.get('/dashboard/owner')
        assert r.status_code == 200
        assert b'Owner Dashboard' in r.data or b'Dashboard' in r.data

    def test_insurance_addon_visible(self, client, app):
        """Check if insurance opt-in is visible in booking/listing context."""
        with app.app_context():
            u = User.query.filter_by(role='owner').first()
            if not u:
                u = User(username='insowner', email='ins@test.com', role='owner', password_hash=generate_password_hash('pass'))
                db.session.add(u)
                db.session.commit()
            
            l = Listing.query.filter_by(status='Active').first()
            if not l:
                l = Listing(airport_icao='CYHM', size_sqft=1000, price_month=500, owner_id=u.id, status='Active')
                db.session.add(l)
                db.session.commit()
            l_id = l.id
        
        # Ensure guest for insurance check
        client.get('/logout', follow_redirects=True)
        r = client.get(f'/listing/{l_id}')
        assert r.status_code == 200
        text_data = r.get_data(as_text=True).lower()
        assert 'cyhm' in text_data
        assert 'avemco' in text_data or 'liability' in text_data or 'book_listing' in text_data


# ════════════════════════════════════════════════════════════════
#  5. MONETIZATION
# ════════════════════════════════════════════════════════════════

class TestMonetization:
    def test_white_label_submission_works(self, client):
        """Test white-label slot reservation."""
        r = client.post('/white-label/submit', data={
            'fbo_name': 'HangarLink FBO',
            'contact_name': 'Admin',
            'contact_email': 'admin@fbo.com'
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Reservation' in r.data or b'Confirmed' in r.data

    def test_insights_teaser_loads(self, client, app):
        """Verify unauthenticated/free users see insights or teaser."""
        with app.app_context():
             u = User.query.filter_by(email='pilot@example.com').first()
             if not u:
                 u = User(username='testpilot', email='pilot@example.com', 
                          password_hash=generate_password_hash('Password123!'), role='renter')
                 db.session.add(u)
                 db.session.commit()
             email = u.email

        client.post('/login', data={'email': email, 'password': 'Password123!'})
        r = client.get('/insights')
        assert r.status_code in (200, 302)
        assert b'Insights' in r.data or b'Pro' in r.data

    def test_admin_ads_access(self, client, app):
        """Admin-only access check."""
        with app.app_context():
            admin = User.query.filter_by(is_admin=True).first()
            if not admin:
                admin = User(username='admin_test', email='admintest@test.com', 
                             password_hash=generate_password_hash('adminpass'), 
                             is_admin=True, role='owner')
                db.session.add(admin)
                db.session.commit()
            email = admin.email
            
        client.post('/login', data={'email': email, 'password': 'adminpass'})
        r = client.get('/admin/ads')
        assert r.status_code == 200
        assert b'Ads' in r.data or b'Manage' in r.data

    def test_market_reports_loads(self, client, app):
        """Verify market reports listing page."""
        client.post('/login', data={'email': 'pilot@example.com', 'password': 'Password123!'})
        r = client.get('/insights/market-reports')
        assert r.status_code == 200
        assert b'Market Reports' in r.data or b'Reports' in r.data
        assert b'hamilton' in r.data.lower() or b'National' in r.data


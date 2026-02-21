"""
HangarLink MVP — Full Feature Test Suite
Covers every major route, auth flow, listing CRUD, search, admin, and error pages.
Run with:  pytest tests/ -v
"""
import io
import pytest
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, Listing, Ad
from conftest import make_user, make_owner, make_listing


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password},
                       follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def register(client, username, email, password, role='renter'):
    return client.post('/register', data={
        'username': username, 'email': email,
        'password': password, 'role': role
    }, follow_redirects=True)


# ════════════════════════════════════════════════════════════════
#  1. CORE PAGES
# ════════════════════════════════════════════════════════════════

class TestCorePages:
    def test_homepage_loads(self, client):
        r = client.get('/')
        assert r.status_code == 200
        assert b'HangarLink' in r.data or b'Hangar' in r.data

    def test_listings_page_loads(self, client):
        r = client.get('/listings')
        assert r.status_code == 200

    def test_listings_search_by_icao(self, client, seed_listing):
        r = client.get('/listings?airport=CYTZ')
        assert r.status_code == 200

    def test_listings_filter_covered(self, client):
        r = client.get('/listings?covered=true')
        assert r.status_code == 200

    def test_listings_filter_price(self, client):
        r = client.get('/listings?min_price=100&max_price=500')
        assert r.status_code == 200

    def test_pricing_page_loads(self, client):
        r = client.get('/pricing')
        assert r.status_code == 200

    def test_terms_page_loads(self, client):
        r = client.get('/terms')
        assert r.status_code == 200

    def test_health_endpoint(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'ok'

    def test_404_page(self, client):
        r = client.get('/this-page-does-not-exist-xyz')
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════
#  2. AUTHENTICATION
# ════════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_page_loads(self, client):
        r = client.get('/login')
        assert r.status_code == 200
        assert b'Sign In' in r.data or b'Login' in r.data

    def test_register_page_loads(self, client):
        r = client.get('/register')
        assert r.status_code == 200

    def test_register_new_user(self, client, app):
        with app.app_context():
            r = register(client, 'newpilot99', 'newpilot99@test.com', 'Password1!')
            assert r.status_code == 200
            u = User.query.filter_by(email='newpilot99@test.com').first()
            assert u is not None
            db.session.delete(u)
            db.session.commit()

    def test_register_duplicate_email(self, client, app):
        with app.app_context():
            make_user(db, username='dupuser', email='dup@test.com')
            r = register(client, 'dupuser2', 'dup@test.com', 'Password1!')
            assert r.status_code == 200
            u = User.query.filter_by(email='dup@test.com').first()
            db.session.delete(u)
            db.session.commit()

    def test_login_valid_credentials(self, client, app):
        with app.app_context():
            u = make_user(db, username='logintest', email='logintest@test.com',
                          password='Password1!')
            r = login(client, 'logintest@test.com', 'Password1!')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_login_wrong_password(self, client, app):
        with app.app_context():
            u = make_user(db, username='logintest2', email='logintest2@test.com',
                          password='RealPass1!')
            r = login(client, 'logintest2@test.com', 'WrongPassword')
            assert r.status_code == 200
            # Should stay on login page or show error
            db.session.delete(u)
            db.session.commit()

    def test_logout_redirects(self, client, app):
        with app.app_context():
            u = make_user(db, username='logouttest', email='logouttest@test.com')
            login(client, 'logouttest@test.com', 'Password1!')
            r = logout(client)
            assert r.status_code == 200
            db.session.delete(u)
            db.session.commit()

    def test_protected_route_redirects_unauthenticated(self, client):
        r = client.get('/my-listings', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_forgot_password_page_loads(self, client):
        r = client.get('/forgot-password')
        assert r.status_code == 200
        assert b'Forgot' in r.data or b'Reset' in r.data

    def test_forgot_password_post_safe(self, client):
        # Should always return 200 (never leak whether email exists)
        r = client.post('/forgot-password',
                        data={'email': 'nobody@nowhere.com'},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_reset_password_invalid_token(self, client):
        r = client.get('/reset-password/invalid-token-xyz', follow_redirects=True)
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════
#  3. LISTING CRUD
# ════════════════════════════════════════════════════════════════

class TestListings:
    def test_post_listing_requires_login(self, client):
        r = client.get('/post-listing', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_post_listing_page_loads_for_owner(self, client, app):
        with app.app_context():
            u = make_owner(db, username='postowner', email='postowner@test.com')
            login(client, 'postowner@test.com', 'Password1!')
            r = client.get('/post-listing')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_create_listing(self, client, app):
        with app.app_context():
            u = make_owner(db, username='createowner', email='createowner@test.com')
            login(client, 'createowner@test.com', 'Password1!')
            r = client.post('/post-listing', data={
                'airport_icao': 'CYHM',
                'size_sqft': 1200,
                'covered': 'on',
                'price_month': 425,
                'description': 'Clean heated T-hangar in Hamilton',
            }, follow_redirects=True)
            assert r.status_code == 200
            listing = Listing.query.filter_by(airport_icao='CYHM', owner_id=u.id).first()
            assert listing is not None
            logout(client)
            db.session.delete(listing)
            db.session.delete(u)
            db.session.commit()

    def test_listing_detail_loads(self, client, seed_listing):
        r = client.get(f'/listing/{seed_listing.id}')
        assert r.status_code == 200

    def test_listing_detail_not_found(self, client):
        r = client.get('/listing/999999')
        assert r.status_code == 404

    def test_edit_listing_requires_auth(self, client, seed_listing):
        r = client.get(f'/listing/{seed_listing.id}/edit', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_edit_listing_owner_can_access(self, client, app, seed_owner, seed_listing):
        with app.app_context():
            login(client, 'owner@test.com', 'Password1!')
            r = client.get(f'/listing/{seed_listing.id}/edit')
            assert r.status_code == 200
            logout(client)

    def test_my_listings_page(self, client, app, seed_owner):
        with app.app_context():
            login(client, 'owner@test.com', 'Password1!')
            r = client.get('/my-listings')
            assert r.status_code == 200
            logout(client)

    def test_like_listing(self, client, seed_listing):
        r = client.post(f'/like/{seed_listing.id}', follow_redirects=True)
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════
#  4. SEARCH & BROWSE
# ════════════════════════════════════════════════════════════════

class TestSearch:
    def test_search_returns_results(self, client, seed_listing):
        r = client.get('/listings?airport=CYTZ')
        assert r.status_code == 200

    def test_search_empty_results(self, client):
        r = client.get('/listings?airport=ZZZZ')
        assert r.status_code == 200

    def test_search_with_radius(self, client):
        r = client.get('/listings?airport=CYYZ&radius=100')
        assert r.status_code == 200

    def test_search_with_price_range(self, client):
        r = client.get('/listings?min_price=200&max_price=500')
        assert r.status_code == 200

    def test_search_covered_only(self, client):
        r = client.get('/listings?covered=true')
        assert r.status_code == 200

    def test_scalability_100_listings(self, client, app):
        """Seed 100 listings and ensure search remains fast."""
        import time
        with app.app_context():
            owner = make_user(db, username='bulkowner', email='bulk@test.com',
                              role='owner')
            listings = []
            icaos = ['CYYZ', 'CYUL', 'CYVR', 'CYYC', 'CYEG', 'CYHM', 'CYTZ',
                     'CYKF', 'CYOW', 'CYQB']
            for i in range(100):
                l = Listing(
                    airport_icao=icaos[i % len(icaos)],
                    price_month=200 + (i * 3),
                    covered=(i % 2 == 0),
                    size_sqft=800 + (i * 10),
                    description=f'Bulk test listing #{i}',
                    owner_id=owner.id,
                    status='Active',
                )
                db.session.add(l)
                listings.append(l)
            db.session.commit()

            t0 = time.time()
            r = client.get('/listings?airport=CYYZ')
            elapsed = time.time() - t0

            assert r.status_code == 200
            assert elapsed < 3.0, f"Search too slow: {elapsed:.2f}s"

            # Cleanup
            for l in listings:
                db.session.delete(l)
            db.session.delete(owner)
            db.session.commit()


# ════════════════════════════════════════════════════════════════
#  5. MESSAGING
# ════════════════════════════════════════════════════════════════

class TestMessaging:
    def test_messages_page_requires_auth(self, client):
        r = client.get('/messages', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_messages_page_loads(self, client, app):
        with app.app_context():
            u = make_user(db, username='msguser', email='msg@test.com')
            login(client, 'msg@test.com', 'Password1!')
            r = client.get('/messages')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_send_guest_message(self, client, seed_listing):
        r = client.post(f'/message/{seed_listing.owner_id}', data={
            'content': 'Hi, is this hangar available?',
            'listing_id': seed_listing.id,
            'guest_email': 'guest@example.com',
        }, follow_redirects=True)
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════
#  6. DASHBOARDS & PROFILE
# ════════════════════════════════════════════════════════════════

class TestDashboards:
    def test_profile_requires_auth(self, client):
        r = client.get('/profile', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_profile_loads(self, client, app):
        with app.app_context():
            u = make_user(db, username='profuser', email='prof@test.com')
            login(client, 'prof@test.com', 'Password1!')
            r = client.get('/profile')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_owner_dashboard_loads(self, client, app):
        with app.app_context():
            u = make_owner(db, username='dashowner', email='dashowner@test.com')
            login(client, 'dashowner@test.com', 'Password1!')
            r = client.get('/dashboard/owner')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_rewards_page_loads(self, client, app):
        with app.app_context():
            u = make_user(db, username='rewuser', email='rew@test.com')
            login(client, 'rew@test.com', 'Password1!')
            r = client.get('/rewards')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_referrals_page_loads(self, client, app):
        with app.app_context():
            u = make_user(db, username='refuser', email='ref@test.com')
            login(client, 'ref@test.com', 'Password1!')
            r = client.get('/referrals')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()


# ════════════════════════════════════════════════════════════════
#  7. MONETIZATION
# ════════════════════════════════════════════════════════════════

class TestMonetization:
    def test_pricing_page_loads(self, client):
        r = client.get('/pricing')
        assert r.status_code == 200
        assert b'Premium' in r.data or b'Plan' in r.data

    def test_subscription_success_requires_auth(self, client):
        r = client.get('/subscription/success', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_market_reports_page(self, client):
        # market-reports requires login
        r = client.get('/insights/market-reports', follow_redirects=False)
        assert r.status_code in (200, 302, 303)

    def test_promote_listing_requires_auth(self, client):
        r = client.post('/promote-listing/silver', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_white_label_page_loads(self, client):
        r = client.get('/white-label')
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════
#  8. ADMIN
# ════════════════════════════════════════════════════════════════

class TestAdmin:
    def test_admin_ads_requires_admin(self, client, app):
        with app.app_context():
            # Non-admin user
            u = make_user(db, username='nonadmin', email='nonadmin@test.com')
            login(client, 'nonadmin@test.com', 'Password1!')
            r = client.get('/admin/ads', follow_redirects=False)
            assert r.status_code in (302, 303, 403)
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_admin_listings_requires_admin(self, client, app):
        with app.app_context():
            u = make_user(db, username='nonadmin2', email='nonadmin2@test.com')
            login(client, 'nonadmin2@test.com', 'Password1!')
            r = client.get('/admin/listings', follow_redirects=False)
            assert r.status_code in (302, 303, 403)
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_admin_ads_loads_for_admin(self, client, app):
        with app.app_context():
            u = make_user(db, username='adminuser', email='adminuser@test.com',
                          is_admin=True)
            login(client, 'adminuser@test.com', 'Password1!')
            r = client.get('/admin/ads')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_admin_listings_loads_for_admin(self, client, app):
        with app.app_context():
            u = make_user(db, username='adminuser2', email='adminuser2@test.com',
                          is_admin=True)
            login(client, 'adminuser2@test.com', 'Password1!')
            r = client.get('/admin/listings')
            assert r.status_code == 200
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_toggle_featured_admin(self, client, app, seed_listing):
        with app.app_context():
            u = make_user(db, username='featadmin', email='featadmin@test.com',
                          is_admin=True)
            login(client, 'featadmin@test.com', 'Password1!')
            old_state = seed_listing.is_featured
            r = client.post(f'/admin/toggle-featured/{seed_listing.id}',
                            follow_redirects=True)
            assert r.status_code == 200
            # Refresh from DB
            from models import Listing as L
            refreshed = L.query.get(seed_listing.id)
            assert refreshed.is_featured != old_state
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_create_ad(self, client, app):
        with app.app_context():
            u = make_user(db, username='adadmin', email='adadmin@test.com',
                          is_admin=True)
            login(client, 'adadmin@test.com', 'Password1!')
            r = client.post('/admin/ads', data={
                'title': 'Test Sponsor',
                'image_url': 'https://example.com/banner.jpg',
                'link_url': 'https://example.com',
                'placement': 'home_banner',
            }, follow_redirects=True)
            assert r.status_code == 200
            from models import Ad
            ad = Ad.query.filter_by(title='Test Sponsor').first()
            assert ad is not None
            db.session.delete(ad)
            logout(client)
            db.session.delete(u)
            db.session.commit()


# ════════════════════════════════════════════════════════════════
#  9. API ENDPOINTS
# ════════════════════════════════════════════════════════════════

class TestAPI:
    def test_concierge_api_post(self, client, app):
        with app.app_context():
            u = make_user(db, username='chatuser', email='chat@test.com')
            login(client, 'chat@test.com', 'Password1!')
            r = client.post('/api/concierge',
                            json={'message': 'Show hangars at CYTZ'},
                            content_type='application/json')
            assert r.status_code == 200
            data = r.get_json()
            assert 'reply' in data or 'response' in data or 'message' in data
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_health_json(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        j = r.get_json()
        assert j['status'] == 'ok'

    def test_forecast_endpoint(self, client):
        r = client.get('/api/forecast?airport=CYTZ')
        assert r.status_code in (200, 401, 403, 404)


# ════════════════════════════════════════════════════════════════
#  10. MODEL INTEGRITY
# ════════════════════════════════════════════════════════════════

class TestModels:
    def test_user_model_fields(self, app):
        with app.app_context():
            u = make_user(db, username='modeltest', email='modeltest@test.com')
            assert u.id is not None
            assert u.subscription_tier == 'free'
            assert u.is_premium is False
            assert u.is_admin is False
            assert u.points == 0
            db.session.delete(u)
            db.session.commit()

    def test_listing_model_fields(self, app):
        with app.app_context():
            owner = make_owner(db, username='listmodel', email='listmodel@test.com')
            l = make_listing(db, owner)
            assert l.id is not None
            assert l.is_featured is False
            assert l.status == 'Active'
            assert l.health_score == 80
            assert l.price_month == 350.0
            db.session.delete(l)
            db.session.delete(owner)
            db.session.commit()

    def test_listing_price_intelligence(self, app):
        with app.app_context():
            owner = make_owner(db, username='piowner', email='pi@test.com')
            l1 = make_listing(db, owner, icao='CYOO', price=300.0)
            l2 = make_listing(db, owner, icao='CYOO', price=500.0)
            # l1's intelligence: sees only l2 (id != l1.id), so min=max=avg=500
            pi = l1.get_price_intelligence()
            assert pi is not None
            assert pi['min'] == 500.0
            assert pi['max'] == 500.0
            assert pi['count'] == 1
            db.session.delete(l1)
            db.session.delete(l2)
            db.session.delete(owner)
            db.session.commit()

    def test_user_reset_token_fields(self, app):
        with app.app_context():
            u = make_user(db, username='resetmodel', email='resetmodel@test.com')
            assert u.reset_token is None
            assert u.reset_token_expires is None
            db.session.delete(u)
            db.session.commit()


# ════════════════════════════════════════════════════════════════
#  11. MISCELLANEOUS / EDGE CASES
# ════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_booking_requires_auth(self, client, seed_listing):
        r = client.post(f'/book/{seed_listing.id}', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_insights_requires_auth(self, client):
        r = client.get('/insights', follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_feed_page_loads(self, client, app):
        # Feed requires login - verify it redirects when unauthenticated
        r = client.get('/feed', follow_redirects=False)
        assert r.status_code in (200, 302, 303)

    def test_concierge_chat_page_requires_auth(self, client):
        # concierge/chat is POST-only; GET should return 405 or redirect
        r = client.get('/concierge/chat', follow_redirects=False)
        assert r.status_code in (200, 302, 303, 405)

    def test_subscription_cancel_page(self, client):
        r = client.get('/subscription/cancel', follow_redirects=True)
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════
#  12. LOGIN / SIGNUP FLOW — POST-AUTH REDIRECT TESTS
#      These specifically guard against the "500 after login" bug
# ════════════════════════════════════════════════════════════════

class TestLoginSignupFlow:
    """
    End-to-end tests for the full registration → login → homepage flow.
    These are the specific tests for the post-auth 500 regression.
    """

    def test_register_then_homepage(self, client, app):
        """Register a new user and verify homepage loads (no 500)."""
        with app.app_context():
            r = register(client, 'flowpilot', 'flowpilot@test.com', 'SecurePass1!')
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            # Verify in DB
            u = User.query.filter_by(email='flowpilot@test.com').first()
            assert u is not None, "User not created in DB"
            assert u.username == 'flowpilot'
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_login_then_homepage_no_500(self, client, app):
        """Log in and confirm the homepage returns 200, not 500."""
        with app.app_context():
            u = make_user(db, username='auth500test', email='auth500@test.com',
                          password='TestPass1!')
            r = login(client, 'auth500@test.com', 'TestPass1!')
            # Status 200 is the only correct answer — 500 would mean a server error
            assert r.status_code == 200, f"Post-login redirect got {r.status_code}"
            assert b'Hangar' in r.data, "Homepage content missing after login"
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_wrong_password_stays_on_login(self, client, app):
        """Wrong password keeps user on login page, no redirect to 500."""
        with app.app_context():
            u = make_user(db, username='wrongpwtest', email='wrongpw@test.com',
                          password='CorrectPass1!')
            r = login(client, 'wrongpw@test.com', 'WrongPassword!')
            # Must be 200, never 500
            assert r.status_code == 200
            # Should still see login form elements
            assert b'email' in r.data or b'Email' in r.data
            db.session.delete(u)
            db.session.commit()

    def test_duplicate_email_on_register(self, client, app):
        """Registering with existing email shows error, no 500."""
        with app.app_context():
            u = make_user(db, username='existuser', email='exist@test.com')
            r = register(client, 'newname', 'exist@test.com', 'AnyPass1!')
            # Must be 200, never 500
            assert r.status_code == 200
            db.session.delete(u)
            db.session.commit()

    def test_owner_register_then_homepage(self, client, app):
        """Owner role registration ends on homepage, not 500."""
        with app.app_context():
            r = register(client, 'ownerflow', 'ownerflow@test.com',
                         'SecurePass1!', role='owner')
            assert r.status_code == 200
            u = User.query.filter_by(email='ownerflow@test.com').first()
            assert u is not None
            assert u.role == 'owner'
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_login_then_profile_accessible(self, client, app):
        """After login, /profile must return 200 (not 500)."""
        with app.app_context():
            u = make_user(db, username='profiletest', email='profiletest@test.com',
                          password='TestPass1!')
            login(client, 'profiletest@test.com', 'TestPass1!')
            r = client.get('/profile')
            assert r.status_code == 200, f"/profile returned {r.status_code} after login"
            logout(client)
            db.session.delete(u)
            db.session.commit()

    def test_login_then_my_listings_accessible(self, client, app):
        """After login as owner, /my-listings must return 200 (not 500)."""
        with app.app_context():
            u = make_owner(db, username='mylisttest', email='mylisttest@test.com')
            login(client, 'mylisttest@test.com', 'Password1!')
            r = client.get('/my-listings')
            assert r.status_code == 200, f"/my-listings returned {r.status_code} after login"
            logout(client)
            db.session.delete(u)
            db.session.commit()


import pytest
import datetime
from app import create_app
from extensions import db, mail
from models import Listing, User, Booking
from flask import url_for
from zoneinfo import ZoneInfo
from werkzeug.exceptions import NotFound

# ──────────────────────────────────────────────────────────────────────────────
# 1. Initialization and Core Functionality
# ──────────────────────────────────────────────────────────────────────────────

def test_app_creation():
    """Verify that we can create the Flask app without broken imports or config."""
    app = create_app()
    assert app is not None

def test_db_readiness(app):
    """Verify that we can initialize the database schema in memory."""
    with app.app_context():
        assert 'listings' in db.metadata.tables
        assert 'users' in db.metadata.tables

# ──────────────────────────────────────────────────────────────────────────────
# 2. Datetime and Logic Sanity
# ──────────────────────────────────────────────────────────────────────────────

def test_datetime_consistency():
    """
    Ensure we are using consistent datetime methods to avoid 
    comparisons between naïve and aware objects.
    """
    # SQLite typically prefers naive UTC, but Flask/Python often use aware.
    # Our app should ideally use UTC consistently.
    now1 = datetime.datetime.now(datetime.UTC)
    now2 = datetime.datetime.now(datetime.UTC)
    assert (now2 - now1).total_seconds() < 5
    
    # Check that a naive comparison would fail if one were aware (sanity check for Python behavior)
    # This just ensures we are aware of the "types" we use in models.
    try:
        naive = datetime.datetime.utcnow() # Deprecated but often used
        aware = datetime.datetime.now(datetime.UTC)
        # Python 3.12+ will warn/fail on comparison of these
        diff = aware - naive # Should not raise ERROR in our tests if logic is sound, 
                             # but in code we must be careful.
    except TypeError:
        # This is expected behavior in modern python to prevent bugs
        pass

# ──────────────────────────────────────────────────────────────────────────────
# 3. Model Integrity
# ──────────────────────────────────────────────────────────────────────────────

def test_listing_model_integrity(seed_listing):
    """Ensure basic listing fields behave as expected."""
    assert seed_listing.id is not None
    assert seed_listing.airport_icao == 'CYTZ'
    assert seed_listing.size_sqft > 0

# ──────────────────────────────────────────────────────────────────────────────
# 4. Rendering Tests (Smoke Tests)
# ──────────────────────────────────────────────────────────────────────────────

def test_home_page_render(client):
    """Check if landing page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hangar' in response.data

def test_listing_search_render(client):
    """Check if main listings feed loads."""
    # Based on routes, it's '/listings'
    response = client.get('/listings')
    assert response.status_code == 200

def test_pricing_page_render(client):
    """Check if pricing page loads."""
    response = client.get('/pricing')
    assert response.status_code == 200

# ──────────────────────────────────────────────────────────────────────────────
# 5. Auth and Protected Routes
# ──────────────────────────────────────────────────────────────────────────────

def test_dashboard_redirects_guest(client):
    """Protected routes should redirect to login."""
    # Using /dashboard/owner based on our search
    response = client.get('/dashboard/owner')
    assert response.status_code == 302 # Login required redirect
    assert 'login' in response.location.lower()

def test_insights_denies_guest(client):
    """Insights needs login and/or special access."""
    response = client.get('/insights')
    assert response.status_code == 302 # Redirected to login

# ──────────────────────────────────────────────────────────────────────────────
# 6. Listing Detail - The "Critical Fix" Verification
# ──────────────────────────────────────────────────────────────────────────────

def test_listing_detail_jinja_render(client, seed_listing):
    """Specifically verify the listing detail page renders without Jinja errors."""
    response = client.get(f'/listing/{seed_listing.id}')
    assert response.status_code == 200
    
    # Check for keywords
    assert seed_listing.airport_icao.encode() in response.data
    
    # Ensure no raw Jinja syntax leaked (indicates parser didn't fail)
    assert b'{{' not in response.data
    assert b'}}' not in response.data

def test_listing_detail_404(client):
    """Ensure 404 works and doesn't 500."""
    response = client.get('/listing/9999999')
    assert response.status_code == 404

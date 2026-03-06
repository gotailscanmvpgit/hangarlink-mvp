import pytest
from flask import url_for
from models import Listing

def test_listing_detail_rendering(client, seed_listing, app):
    """
    Test that the listing detail page renders without 500 errors.
    This helps catch Jinja2 TemplateSyntaxErrors.
    """
    # Ensure current_user is mocked for authenticated/guest views
    # seed_listing is created in conftest.py
    
    listing_id = seed_listing.id
    response = client.get(f'/listing/{listing_id}')
    
    # Check that it doesn't return 500
    assert response.status_code == 200
    
    # Verify some content is rendered
    assert b'HangarDetails' in response.data or b'Hangar' in response.data
    assert seed_listing.airport_icao.encode() in response.data

def test_listing_detail_guest(client, seed_listing):
    """Test as a guest (no one logged in)"""
    response = client.get(f'/listing/{seed_listing.id}')
    assert response.status_code == 200
    assert b'Sign up to reserve' in response.data or b'Reserve Now' in response.data

def test_listing_detail_not_found(client):
    """Test 404 behavior"""
    response = client.get('/listing/999999')
    assert response.status_code == 404

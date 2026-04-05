from app import app, db
from models import Listing

with app.app_context():
    cyhm_listings = Listing.query.filter(Listing.airport_icao.ilike('%CYHM%')).all()
    print(f"Found {len(cyhm_listings)} listings for CYHM")
    for l in cyhm_listings:
        print(f"ID: {l.id}, Title: {l.title}, State: {l.state}, Corridors: {l.corridor_ids}")

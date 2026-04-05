from app import app, db
from models import Listing

with app.app_context():
    all_listings = Listing.query.all()
    print(f"Total Listings: {len(all_listings)}")
    for l in all_listings:
        print(f"ID: {l.id}, ICAO: {l.airport_icao}, State: {l.state}, Corridors: {l.corridor_ids}")

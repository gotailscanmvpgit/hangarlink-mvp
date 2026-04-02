from app import create_app
from extensions import db
from models import Listing

app = create_app()
with app.app_context():
    listings = Listing.query.filter_by(is_featured=True).all()
    print(f"Featured Listings Count: {len(listings)}")
    for l in listings:
        print(f"ID: {l.id}, ICAO: {l.airport_icao}, Photos: '{l.photos}'")

from app import create_app
from extensions import db
from models import Listing
from airport_coords import get_coords
import logging

def backfill_coords():
    app = create_app()
    with app.app_context():
        listings = Listing.query.all()
        updated = 0
        skipped = 0
        unknown = 0
        
        print(f"Checking {len(listings)} listings for missing coordinates...")
        
        for l in listings:
            if l.lat is None or l.lon is None:
                lat, lon, found = get_coords(l.airport_icao)
                if found:
                    l.lat = lat
                    l.lon = lon
                    updated += 1
                else:
                    unknown += 1
                    # Use Toronto default but maybe keep it Null if we want to distinguish?
                    # For now, let's use the default as intended by the system.
                    l.lat = lat
                    l.lon = lon
            else:
                skipped += 1
        
        db.session.commit()
        print(f"Backfill complete:")
        print(f" - Updated: {updated}")
        print(f" - Already had coords: {skipped}")
        print(f" - Unknown ICAOs (used fallback): {unknown}")

if __name__ == '__main__':
    backfill_coords()

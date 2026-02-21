"""
delete_fake_listings.py
Safely removes all test/fake hangar listings from the HangarLinks database.
Fake listings are identified by descriptions containing "Test hangar".
"""

from app import app, db
from models import Listing


def delete_fake_listings():
    with app.app_context():
        # Find all fake listings
        fake_listings = Listing.query.filter(
            Listing.description.ilike('%Test hangar%')
        ).all()

        count = len(fake_listings)

        if count == 0:
            print("✅ No fake listings found. Database is already clean.")
            return

        print(f"⚠️  Found {count} fake/test listings to delete.")
        print("    (Listings whose description contains 'Test hangar')")
        print()

        # Sample preview — show first 5
        preview = fake_listings[:5]
        print("Preview (first 5):")
        for l in preview:
            print(f"  ID {l.id:>6} | {l.airport_icao} | ${l.price_month:.0f}/mo | {l.description[:50]}")
        if count > 5:
            print(f"  ... and {count - 5} more.")
        print()

        # Confirmation
        confirm = input(f"Type 'yes' to delete all {count} fake listings: ").strip().lower()
        if confirm != 'yes':
            print("❌ Aborted. No listings were deleted.")
            return

        # Delete
        deleted = Listing.query.filter(
            Listing.description.ilike('%Test hangar%')
        ).delete(synchronize_session=False)

        db.session.commit()

        remaining = Listing.query.count()
        print(f"\n✅ Deleted {deleted} fake listings successfully.")
        print(f"📊 Remaining listings: {remaining}")


if __name__ == "__main__":
    delete_fake_listings()

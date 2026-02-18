from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as conn:
            # List of indexes that might be conflicting
            indexes = [
                'idx_airport', 'idx_price', 'idx_status', 'idx_created', 
                'idx_owner', 'idx_covered', 'idx_featured', 'idx_premium_listing'
            ]
            for idx in indexes:
                try:
                    conn.execute(text(f"DROP INDEX IF EXISTS {idx}"))
                    print(f"Dropped index: {idx}")
                except Exception as e:
                    print(f"Could not drop {idx} (might not exist): {e}")
            conn.commit()
        print("SUCCESS: Cleaned up conflicting indexes.")
    except Exception as e:
        print(f"ERROR: {e}")

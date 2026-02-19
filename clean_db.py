from app import app, db
from sqlalchemy import text, inspect

def clean_database():
    with app.app_context():
        # Check if alembic_version exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'alembic_version' in tables:
            print("Database already initialized (alembic_version found). Skipping cleanup.")
            return

        print("Fresh install detected. Cleaning up partial tables if any...")
        
        # Drop tables that might conflict with new initial migration
        tables_to_drop = ['users', 'listings', 'bookings', 'messages', 'ad', 'white_label_request']
        for table in tables_to_drop:
            try:
                # Remove CASCADE for SQLite compatibility (Postgres ignores missing CASCADE on DROP TABLE usually, or we add it back if we detect Postgres?)
                # Actually, standard SQL DROP TABLE x CASCADE is valid in Postgres.
                # Forcing CASCADE for Postgres:
                if db.engine.dialect.name == 'postgresql':
                    db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                else:
                    db.session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"Dropped {table} table.")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
                
        db.session.commit()
        print("Database cleanup complete.")

if __name__ == "__main__":
    clean_database()

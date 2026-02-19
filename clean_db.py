from app import app, db
from sqlalchemy import text

def clean_database():
    with app.app_context():
        print("Cleaning up database migration artifacts...")
        
        # Drop alembic_version table to reset migration history
        try:
            db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            print("Dropped alembic_version table.")
        except Exception as e:
            print(f"Error dropping alembic_version: {e}")
            
        # Drop tables that might conflict with new initial migration
        tables_to_drop = ['ad', 'white_label_request']
        for table in tables_to_drop:
            try:
                db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"Dropped {table} table.")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
                
        db.session.commit()
        print("Database cleanup complete.")

if __name__ == "__main__":
    clean_database()

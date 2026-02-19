from app import app, db
from sqlalchemy import text, inspect

def clean_database():
    with app.app_context():
        # Check if alembic_version exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Check if alembic_version exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        needs_cleanup = False
        
        if 'alembic_version' in tables:
            # Check if the revision in DB matches local migration history
            try:
                # Get current revision from DB
                db_rev = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
                print(f"Current DB revision: {db_rev}")
                
                # Check if this revision file exists locally
                import os
                migrations_dir = os.path.join(app.root_path, 'migrations', 'versions')
                # Find any file containing this revision ID
                found = False
                if os.path.exists(migrations_dir):
                    for filename in os.listdir(migrations_dir):
                        if db_rev in filename:
                            found = True
                            break
                
                if found:
                    print(f"Revision {db_rev} found locally. Database is consistent.")
                    return # All good
                else:
                    print(f"Revision {db_rev} NOT found locally (Zombie revision). Triggering cleanup.")
                    needs_cleanup = True
            except Exception as e:
                print(f"Error checking revision: {e}")
                needs_cleanup = True # Assume inconsistent if error
        else:
            print("No alembic_version table found. Fresh install detected.")
            needs_cleanup = True

        if needs_cleanup:
            print("Cleaning up database (dropping tables)...")
            # Drop alembic_version first
            try:
                db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            except Exception as e:
                print(f"Error dropping alembic_version: {e}")
            
            # Drop tables that might conflict with new initial migration
            tables_to_drop = ['users', 'listings', 'bookings', 'messages', 'ad', 'white_label_request']
            for table in tables_to_drop:
                try:
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

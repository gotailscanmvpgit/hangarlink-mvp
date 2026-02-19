from app import app, db
from sqlalchemy import text, inspect
import os

def clean_database():
    with app.app_context():
        print("Checking database state...")
        # Check if alembic_version exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        needs_cleanup = False
        
        if 'alembic_version' in tables:
            # Check if the revision in DB matches local migration history
            try:
                # Use engine connection for queries
                with db.engine.connect() as conn:
                    result = conn.execute(text("SELECT version_num FROM alembic_version"))
                    db_rev = result.scalar()
                    print(f"Current DB revision: {db_rev}")
                    
                    # Check if this revision file exists locally
                    migrations_dir = os.path.join(app.root_path, 'migrations', 'versions')
                    
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
            # Check if partial tables exist (e.g. users) even if alembic_version missing
            if 'users' in tables:
                print("Partial tables found without version control. Cleaning up.")
                needs_cleanup = True

        if needs_cleanup:
            print("Cleaning up database (dropping tables)...")
            
            try:
                # Use a specific connection for DDL
                with db.engine.connect() as conn:
                    # Start transaction explicitly if needed, or rely on auto-commit for DDL?
                    # SQLAlchemy < 2.0 uses connection.begin() implicitly or explicitly.
                    # SQLAlchemy 2.0 uses connection context manager which commits or rolls back on exit?
                    # But text() execution on connection is usually autocommit unless in transaction.
                    # We will use explicit transaction.
                    trans = conn.begin()
                    try:
                        # Drop alembic_version first
                        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                        
                        # Drop tables that might conflict
                        tables_to_drop = ['users', 'listings', 'bookings', 'messages', 'ad', 'white_label_request']
                        for table in tables_to_drop:
                            # Forcing CASCADE for Postgres
                            if db.engine.dialect.name == 'postgresql':
                                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                            else:
                                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                            print(f"Dropped {table} table.")
                        
                        trans.commit()
                        print("Database cleanup complete.")
                    except Exception as e:
                        trans.rollback()
                        print(f"Error during cleanup transaction: {e}")
                        # We must exit with error to stop deployment if cleanup fails
                        # But if we exit 1, deployment fails. Maybe that's good?
                        # Yes, better to fail fast than boot into broken state.
                        raise e
            except Exception as e:
                print(f"Database cleanup FAILED: {e}")
                import sys
                sys.exit(1)

if __name__ == "__main__":
    clean_database()

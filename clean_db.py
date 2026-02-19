from app import app, db
from sqlalchemy import text

def reset_migrations():
    """
    Simple, direct database migration reset.
    Always drops alembic_version and all app tables on startup.
    Safe to run repeatedly - uses IF EXISTS.
    """
    with app.app_context():
        print("=== DB RESET: Starting forced cleanup ===")
        
        with db.engine.connect() as conn:
            with conn.begin():
                # Step 1: Drop alembic_version to allow clean migration
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                print("Dropped alembic_version")
                
                # Step 2: Drop all app tables (CASCADE handles foreign keys on Postgres)
                if db.engine.dialect.name == 'postgresql':
                    tables = ['users', 'listings', 'bookings', 'messages', 'ad', 'white_label_request']
                    for table in tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                        print(f"Dropped {table}")
                else:
                    tables = ['bookings', 'messages', 'listings', 'users', 'ad', 'white_label_request']
                    for table in tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                        print(f"Dropped {table}")
        
        print("=== DB RESET: Complete ===")

if __name__ == "__main__":
    reset_migrations()

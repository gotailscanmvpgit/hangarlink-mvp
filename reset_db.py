"""
Direct database reset using raw psycopg2 - bypasses Flask/SQLAlchemy/Alembic entirely.
Drops all tables so flask db upgrade can create them fresh.
"""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("psycopg2 not available, trying psycopg2-binary...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
    import psycopg2

def reset():
    database_url = os.environ.get('DATABASE_URL', '')
    
    if not database_url:
        print("No DATABASE_URL - assuming local SQLite, skipping reset")
        return
    
    # Railway uses postgres:// but psycopg2 needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"Connecting to PostgreSQL...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True  # DDL needs autocommit in Postgres
        cur = conn.cursor()
        
        print("Dropping tables...")
        tables = [
            'alembic_version',
            'bookings',
            'messages', 
            'listings',
            'users',
            'ad',
            'white_label_request'
        ]
        
        for table in tables:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  Dropped: {table}")
        
        cur.close()
        conn.close()
        print("Database reset complete.")
        
    except Exception as e:
        print(f"Reset failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset()

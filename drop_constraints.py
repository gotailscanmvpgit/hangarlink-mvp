from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Dropping tables to fix SQLite migration conflict...")
    with db.engine.connect() as conn:
        # Drop version tracking table
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        # Drop temporary table likely created by failed migration
        conn.execute(text('DROP TABLE IF EXISTS _alembic_tmp_white_label_request'))
        # Drop temporary ad table if it exists (previous issue)
        conn.execute(text('DROP TABLE IF EXISTS _alembic_tmp_ad'))
        
        conn.commit()
    print("Dropped problematic tables successfully.")
    print("You can now run 'flask db migrate -m \"Fresh migration\"' and 'flask db upgrade'.")

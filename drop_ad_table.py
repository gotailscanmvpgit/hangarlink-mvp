from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Dropping tables to fix migration conflict...")
    with db.engine.connect() as conn:
        # Drop 'ad' table
        conn.execute(text('DROP TABLE IF EXISTS ad'))
        print("Dropped 'ad' table successfully")
        
        # Drop 'white_label_request' table to clear schema mismatch
        conn.execute(text('DROP TABLE IF EXISTS white_label_request'))
        print("Dropped 'white_label_request' table successfully")
        
        # Drop 'alembic_version' to reset history
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        print("Dropped 'alembic_version' table successfully")
        
        # Cleanup potential temp tables
        conn.execute(text('DROP TABLE IF EXISTS _alembic_tmp_ad'))
        conn.execute(text('DROP TABLE IF EXISTS _alembic_tmp_white_label_request'))
        
        conn.commit()
    print("Cleanup complete. You can now delete 'migrations' folder and re-init.")

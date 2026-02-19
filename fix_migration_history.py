from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Dropping 'alembic_version' table to reset migration history...")
    with db.engine.connect() as conn:
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        conn.commit()
    print("Dropped 'alembic_version' successfully.")
    print("You can now run 'flask db stamp head' (if migrations exist) or just 'flask db migrate' if starting fresh.")

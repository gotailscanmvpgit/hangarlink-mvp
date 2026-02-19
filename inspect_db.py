from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Inspecting listings table schema...")
    with db.engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(listings)"))
        columns = [row[1] for row in result]
        print("Columns in listings table:", columns)

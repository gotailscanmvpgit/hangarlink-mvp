from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # 1. Drop temp table
        with db.engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_ad"))
            conn.commit()
        print("SUCCESS: Dropped _alembic_tmp_ad")
    except Exception as e:
        print(f"ERROR dropping table: {e}")

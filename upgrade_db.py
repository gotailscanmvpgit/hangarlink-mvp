import sqlite3
import time

def upgrade_db():
    conn = sqlite3.connect('hangarlink.db', timeout=10)
    try:
        conn.execute('ALTER TABLE listings ADD COLUMN available_sqft FLOAT')
        conn.execute('UPDATE listings SET available_sqft = size_sqft WHERE available_sqft IS NULL')
        conn.commit()
        print("Database upgraded successfully!")
    except Exception as e:
        print(f"Error upgrading db: {e}")
        # Could be duplicate column
        conn.execute('UPDATE listings SET available_sqft = size_sqft WHERE available_sqft IS NULL')
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db()

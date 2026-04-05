import sqlite3
import os

db_path = 'instance/hangarlink.db'
if not os.path.exists(db_path):
    print(f"{db_path} does not exist")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute('SELECT id, airport_icao, state, corridor_ids FROM listings')
    rows = cursor.fetchall()
    print(f"Total Listings: {len(rows)}")
    for row in rows:
        print(row)
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()

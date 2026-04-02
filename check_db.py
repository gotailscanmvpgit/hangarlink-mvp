import sqlite3
import os

db_path = 'instance/hangarlink.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist.")
else:
    print(f"File: {db_path}")
    print(f"Size: {os.path.getsize(db_path)} bytes")
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables:", [t[0] for t in tables])
    if 'users' in [t[0] for t in tables]:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print(f"User count: {count}")
    conn.close()

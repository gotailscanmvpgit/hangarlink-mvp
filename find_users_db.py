import sqlite3
import os

def check_all_dbs():
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                db_path = os.path.join(root, file)
                try:
                    conn = sqlite3.connect(db_path)
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                    table_names = [t[0] for t in tables]
                    if 'users' in table_names:
                        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                        print(f"File: {db_path} | User count: {count} | Tables: {table_names}")
                    else:
                        print(f"File: {db_path} | No users table.")
                    conn.close()
                except Exception as e:
                    print(f"File: {db_path} | Error: {e}")

if __name__ == '__main__':
    check_all_dbs()

#!/bin/bash
set -e
echo "=== DEPLOY: Starting database reset ==="
python clean_db.py
echo "=== DEPLOY: Running migrations ==="
flask db upgrade
echo "=== DEPLOY: Starting server ==="
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app

"""
Entry point for local development.
Imports the already-created `app` from app.py — does NOT call create_app() again,
which would trigger _safe_migrate twice.
"""
import os
from app import app  # app is created once at module level in app.py

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

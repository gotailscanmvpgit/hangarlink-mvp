# Render Deployment Fix - Stripe Dependency

## ✅ Changes Applied

### 1. Updated `requirements.txt`
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Werkzeug==3.0.1
WeasyPrint==60.1
gunicorn==21.2.0
stripe==7.0.0  ← ADDED
```

### 2. Updated `routes.py` (Lines 8-15)
Wrapped stripe import in try/except to prevent crashes:
```python
import os
try:
    import stripe
    # Stripe Config
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
except ImportError:
    stripe = None
from datetime import datetime, date, timedelta
```

### 3. Verified Deployment Files
- ✅ **Procfile**: `web: gunicorn --bind 0.0.0.0:$PORT app:app`
- ✅ **runtime.txt**: `python-3.12.3`

## 🚀 Deployment Status
- **Commit**: `5374f9f` - "Fix Render deployment: Add stripe dependency and wrap import"
- **Pushed to**: `main` branch on GitHub

---

## 👉 Next Steps in Render Dashboard

1. **Trigger Deploy**:
   - Go to your Render service
   - Click **Manual Deploy** → **Deploy latest commit**
   
2. **Watch Build Logs** for:
   - ✅ `Installing collected packages: ... stripe ...`
   - ✅ `Successfully installed stripe-7.0.0`
   - ✅ `Starting gunicorn`
   - ✅ `Listening at: http://0.0.0.0:10000`

3. **Environment Variables** (Optional for MVP):
   - `STRIPE_SECRET_KEY` - Only needed if you want real Stripe payments
   - If not set, the booking flow uses mock sessions

4. **Visit Live URL** once status shows **"Live"**

---

## 🧪 Testing Checklist

Once deployed:
- [ ] Homepage loads
- [ ] Register/Login works
- [ ] Post a listing
- [ ] Browse listings
- [ ] Send a message
- [ ] Try booking (will use mock Stripe if no key set)

---

## ⚠️ Notes

- **Stripe is optional for MVP**: The code gracefully falls back to mock sessions if `STRIPE_SECRET_KEY` is not set
- **WeasyPrint**: May require system dependencies on Render. If PDF generation fails, we can address separately
- **SQLite**: Database is ephemeral on free tier (resets on deploy)

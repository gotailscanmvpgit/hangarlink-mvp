# Render Deployment Guide

## ✅ OPTION 1: Root Structure (IMPLEMENTED)

All Python files have been moved to the project root for simplified deployment.

### Files Updated:
- **Procfile**: `web: gunicorn --bind 0.0.0.0:$PORT app:app`
- **app.py**: Updated paths for `templates/`, `static/`, and database
- **Structure**: All `.py` files now in root (no `code/` folder)

### Render Dashboard Settings:
1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: Leave empty (uses Procfile) OR set to:
   ```
   gunicorn --bind 0.0.0.0:$PORT app:app
   ```
3. **Environment Variables**:
   - `PYTHON_VERSION` = `3.12.3`
   - `SECRET_KEY` = `[Generate a random 32-character string]`
   - `DATABASE_URL` = (Optional, defaults to SQLite)

### Deploy Steps:
1. ✅ Code pushed to GitHub (commit `c7e02eb`)
2. Go to Render Dashboard → Your Service
3. Click **Manual Deploy** → **Deploy latest commit**
4. Watch logs for: `"Running on http://0.0.0.0:10000"` or similar
5. Once "Live", visit your URL

---

## 🔄 OPTION 2: Keep Code Folder (Fallback)

If you need to revert to the `code/` folder structure:

### Render Dashboard Start Command:
```bash
gunicorn --pythonpath code --bind 0.0.0.0:$PORT app:app
```

### OR use this Procfile:
```
web: gunicorn --chdir code --bind 0.0.0.0:$PORT app:app
```

---

## 🧪 Testing After Deploy

1. **Homepage**: Should load instantly
2. **Register**: Create account → See onboarding tour
3. **PWA**: On mobile, see "Install HangarLink" banner
4. **Listings**: Post a listing to verify database writes

## ⚠️ Important Notes

- **Free Tier Sleep**: App sleeps after 15 min inactivity (~30s wake time)
- **SQLite Ephemeral**: Database resets on each deploy (use Postgres for persistence)
- **Logs**: Check Render logs if you see errors

---

## 📋 Current File Structure

```
HangarLink-MVP-2025/
├── app.py              ← Main Flask app
├── extensions.py       ← DB & login manager
├── models.py          ← User, Listing models
├── routes.py          ← All routes
├── config.py          ← Config (if exists)
├── requirements.txt   ← Dependencies
├── runtime.txt        ← Python 3.12.3
├── Procfile           ← Gunicorn start command
├── templates/         ← HTML templates
├── static/            ← CSS, JS, images
└── hangarlink.db      ← SQLite database
```

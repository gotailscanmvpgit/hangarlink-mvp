# 🚀 Railway Deployment Guide for HangarLink

This guide details how to deploy your Flask + PostgreSQL application to Railway (Railway.app).

## 1. Prerequisites
I have already prepared the necessary configuration files for you:
*   `Procfile`: Specifies the start command (`web: flask db upgrade && gunicorn app:app`).
*   `runtime.txt`: Sets Python version to 3.12.3.
*   `requirements.txt`: Includes `gunicorn` and `psycopg2-binary`.

## 2. Step-by-Step Deployment

### Step 1: Push Code to GitHub
Ensure all your local changes (including the new `Procfile` and `runtime.txt`) are pushed to your GitHub repository.
```bash
git add .
git commit -m "Configure for Railway deployment"
git push origin main
```

### Step 2: Create Project on Railway
1.  Log in to [Railway.app](https://railway.app/).
2.  Click **New Project** → **Deploy from GitHub repo**.
3.  Select your repository (`hangarlink-mvp`).
4.  Click **Deploy Now**.
    *   *Note:* The initial build might fail because the database isn't connected yet. This is normal.

### Step 3: Add PostgreSQL Database
1.  In your Railway project dashboard, click **New** → **Database** → **PostgreSQL**.
2.  Wait for the database to be provisioned (usually takes 10-30 seconds).

### Step 4: Configure Environment Variables
1.  Open your **Web Service** settings (click on the `hangarlink-mvp` card).
2.  Go to the **Variables** tab.
3.  Add the following variables:
    *   `DATABASE_URL`: Often auto-filled. If not, copy the "Connection String" from your PostgreSQL service variables. **Ensure strict format:** `postgresql://...` (Railway provides `DATABASE_URL`, which is usually correct).
    *   `SECRET_KEY`: Generate a random string (e.g., `openssl rand -hex 32`).
    *   `FLASK_DEBUG`: `0` (Production mode).
    *   `STRIPE_SECRET_KEY`: Your Stripe secret key (`sk_test_...`).
    *   `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key (`pk_test_...`).

### Step 5: Redploy
1.  Go to the **Deployments** tab.
2.  Click **Redeploy** (if the initial build failed).
3.  Wait for the build logs to show success.

## 3. Verify Deployment
1.  Click the generated URL (usually `https://hangarlink-mvp-production.up.railway.app` or similar).
2.  The app should load.
3.  **Seed Data:**
    *   Railway doesn't have a direct "Shell" tab like Render.
    *   To seed data, we recommend installing the Railway CLI locally: `npm i -g @railway/cli`.
    *   Then run: `railway run python seed_data.py`.
    *   Alternatively, use a tool like **pgAdmin** or **TablePlus** to connect to your remote database and run SQL scripts if needed, OR add a temporary route in `app.py` to seed data (less secure).
    *   **Recommended:** Use the CLI method.

## 4. Troubleshooting
*   **Application Error:** Check the **Deploy Logs**.
*   **Database Connection Error:** Ensure `DATABASE_URL` starts with `postgresql://` (not `postgres://`). The app handles this automatically, but double-check.
*   **Missing Module:** Ensure `requirements.txt` lists all dependencies.
*   **500 Internal Server Error:** Often due to missing environment variables (e.g., Stripe keys). Check logs for details.

---
**Status:** Ready to deploy! 🚀

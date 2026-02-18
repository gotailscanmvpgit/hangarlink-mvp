# 🚀 Railway Deployment Guide for HangarLink

This guide details how to deploy your Flask + PostgreSQL application to Railway (Railway.app).

## 1. Prerequisites
I have already prepared the necessary configuration files for you:
*   `Procfile`: Specifies the start command (`web: gunicorn --bind 0.0.0.0:$PORT app:app`).
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

### Step 3: Add PostgreSQL Database
1.  In your Railway project dashboard, click **New** → **Database** → **PostgreSQL**.
2.  Wait for the database to be provisioned.
3.  Right-click the database -> **Settings** -> **Copy Connection String** (if needed) or verify it's linked.

### Step 4: Configure Environment Variables
1.  Open your **Web Service** settings (click on the `hangarlink-mvp` card).
2.  Go to the **Variables** tab.
3.  Add the following variables:
    *   `SECRET_KEY`: Generate a random string.
    *   `FLASK_DEBUG`: `0`.
    *   `STRIPE_SECRET_KEY`: Your Stripe secret key.
    *   `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key.
    *   `DATABASE_URL`: Typically auto-set by Railway. If not, paste your Postgres connection string.

### Step 5: Run Database Migrations (Crucial)
Since we removed auto-migration from the start command, you must run this manually initially:
1.  Install Railway CLI locally: `npm i -g @railway/cli`.
2.  Login: `railway login`.
3.  Link project: `railway link`.
4.  Run migrations:
    ```bash
    railway run flask db upgrade
    ```

## 3. Verify Deployment
1.  Open the public URL.
2.  **Seed Data:**
    *   Run: `railway run python seed_data.py`.


## 4. Troubleshooting
*   **Application Error:** Check the **Deploy Logs**.
*   **Database Connection Error:** Ensure `DATABASE_URL` starts with `postgresql://` (not `postgres://`). The app handles this automatically, but double-check.
*   **Missing Module:** Ensure `requirements.txt` lists all dependencies.
*   **500 Internal Server Error:** Often due to missing environment variables (e.g., Stripe keys). Check logs for details.

---
**Status:** Ready to deploy! 🚀

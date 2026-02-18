# 🚀 HangarLink Deployment Guide

Each time you push changes to GitHub, Render automatically starts a deployment.

## 1. Monitor Deployment
Your deployment was triggered by the recent git push.
1.  Go to your **[Render Dashboard](https://dashboard.render.com/)**.
2.  Click on your **HangarLink** web service.
3.  Click on **Events** or **Logs** in the sidebar.
4.  Look for a "Deploy started" event for commit `d6f09ea` (or later).
5.  Wait until you see **"Your service is live"** in the logs (usually 2-5 minutes).

## 2. Seed Production Data (Crucial Step)
Since the production database resets on redeployment (with ephemeral storage), you must re-seed data.
1.  In the Render Dashboard, click on the **Shell** tab (top menu).
2.  Wait for the terminal prompt to appear.
3.  Run the following command:
    ```bash
    python seed_data.py
    ```
4.  Wait for the confirmation output:
    - "Users Created: ... - Admin"
    - "Listings Created"

## 3. Verify Live Site
1.  Open your live URL (e.g., `https://hangarlink-...onrender.com`).
2.  **Log In:** `admin@hangarlink.com` / `password`.
3.  **Check Ads:** Verify the homepage banner exists.
4.  **Check Reports:** Go to `/insights/market-reports`.

**Troubleshooting:**
- **500 Error?** Check Logs -> ensure `STRIPE_SECRET_KEY` is set in Environment Variables.
- **Can't seed?** Ensure the `instance` folder exists (fixed in commit `d6f09ea`).

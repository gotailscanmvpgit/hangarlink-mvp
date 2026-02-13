# HangarLink Tier 3 Features Testing Guide

Congratulations! You've unlocked the full enterprise suite.

## 1. Admin & Advertising
Log in as the new Administrator account:
- **Email:** `admin@hangarlink.com`
- **Password:** `password`

### Manage Ads:
1.  Navigate to `/admin/ads` (or type in URL).
2.  You will see the Ad Management Dashboard.
3.  Create a new ad:
    - **Title:** "Test Promo"
    - **Placement:** "home_banner" or "sidebar"
    - **Image URL:** `https://placehold.co/600x200/001F3F/FFF?text=Test+Ad`
    - **Link URL:** `https://google.com`
4.  Go to the **Homepage** (`/`) to see the new banner ad.
5.  Go to **Listings** (`/listings`) to see sidebar ads (in-feed).

## 2. White-Label Requests (B2B)
1.  Log out or open incognito window.
2.  Navigate to `/white-label`.
3.  You will see the premium "Partner Application" page.
4.  Fill out the form and submit.
5.  (Admin check: In a real app, you'd see this in admin panel. For MVP, check database or logs).

## 3. Market Intelligence (Data Licensing)
1.  Log in as **Premium User** (`premium@hangarlink.com` / `password`) OR as **Admin**.
2.  Navigate to `/insights/market-reports`.
3.  You will see the **Market Intelligence Reports** dashboard.
4.  Click "Download Data" on any report (mock functionality).
5.  Verify that non-premium users (e.g., `owner@test.com`) are redirected to the teaser page (`/insights`).

## Notes
- **Database Reset:** The database was reset to `hangarlink_v3.db` to apply new schemas. All previous data is gone. New seed data is active.
- **Stripe:** Ensure your `.env` keys are set for checkouts to work.

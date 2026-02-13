# HangarLink Tier 2 Features Access Guide

Implementations for Featured Listings, Insurance Add-ons, and Premium Analytics are strictly integrated with Stripe (Test Mode).

## 1. Prerequisites
Ensure your `.env` file has the Stripe Test keys:
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Restart the Flask application** to apply the new database models and routes.

## 2. Sponsored Listings (Featured)
**Goal:** Boost listing visibility.

1.  **Navigate:** Log in as an owner and go to **Premium** (top nav) or `/pricing/sponsored`.
2.  **Select:** Choose a listing from the dropdown.
3.  **Purchase:** Select a tier (Silver $49, Gold $99, Platinum $199).
    *   *Stripe Checkout will open.*
    *   Use test card: `4242 4242 4242 4242`.
4.  **Verify:**
    *   You are redirected to the listing detail.
    *   See the **"Featured"** badge (gradient bolt icon) on the listing card in `/listings`.
    *   See the listing at the **top** of the search results in `/listings`.

## 3. Insurance Add-On
**Goal:** Renter purchases short-term liability coverage.

1.  **Navigate:** Log in as a renter and view any active listing.
2.  **Reserve:** Click "Reserve Now" (or view the booking form).
3.  **Opt-in:** Check the box **"Add Liability Insurance"** (Avemco Partner).
    *   *Note: Adds $45 base + $15/day fee.*
4.  **Checkout:** Click "Reserve Now".
    *   *Stripe Checkout will open.*
    *   Verify the line item "Short-Term Hangar Insurance" is present.
    *   Total price includes the insurance fee.

## 4. Analytics & Insights
**Goal:** Access market data dashboard.

1.  **Navigate:** Click **"Insights"** in the top navigation bar (or user menu).
2.  **Paywall:** If not premium, you see the "Teaser" page with blurred charts.
3.  **Purchase:** Click "Unlock Report ($19.99)" or "Pro Access ($99/yr)".
    *   *Stripe Checkout will open.*
    *   Use test card.
4.  **Dashboard:**
    *   After payment, you access the full **Market Insights Dashboard**.
    *   View real-time (mock) charts for Price Trends and Occupancy.
    *   See AI Recommendations.

## 5. Technical Notes
*   **Charts:** Uses Chart.js (CDN).
*   **Database:** New fields `is_featured`, `insurance_opt_in`, `has_analytics_access` added.
*   **Sorting:** `/listings` query updated to sort by `is_featured DESC`, `is_premium DESC`, `created_at DESC`.

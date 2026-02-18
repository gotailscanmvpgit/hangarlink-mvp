# 💰 HangarLink Monetization Guide

## Overview

HangarLink now includes a full monetization system with **subscription plans** and **transaction fees**, powered by **Stripe**.

---

## 🏗️ Architecture

### Subscription Plans

| Plan | Price | For | Features |
|------|-------|-----|----------|
| **Free** | $0/mo | Everyone | 1 listing (owners), 5 searches/day (renters), basic messaging |
| **Owner Premium** | $9.99/mo | Hangar owners | Unlimited listings, priority placement, analytics, premium badge, verified fast-track |
| **Renter Premium** | $6.99/mo | Renters | Unlimited searches, saved alerts, priority support, premium badge, early access |

### Transaction Fee

- **8% platform fee** charged to the renter on each completed booking
- Example: $1,500/mo rental → $120 platform fee
- Fee is transparent and shown on listing detail pages and at checkout

---

## 🔑 Stripe Setup (Test Mode)

### Step 1: Get Stripe API Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
2. Sign up / log in
3. Make sure **"Test mode"** is toggled ON (top right)
4. Copy your keys:
   - **Publishable key**: `pk_test_...`
   - **Secret key**: `sk_test_...`

### Step 2: Add Keys Locally

Create a `.env` file in the project root:

```env
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
```

### Step 3: Add Keys to Render

1. Go to your [Render Dashboard](https://dashboard.render.com)
2. Select your HangarLink service
3. Go to **Environment** → **Add Environment Variable**
4. Add:
   - `STRIPE_SECRET_KEY` = `sk_test_...`
   - `STRIPE_PUBLISHABLE_KEY` = `pk_test_...`
5. Click **Save Changes** (triggers auto-deploy)

### Step 4: Test Checkout

Use Stripe's test card numbers:

| Card Number | Result |
|-------------|--------|
| `4242 4242 4242 4242` | Succeeds |
| `4000 0000 0000 0002` | Declined |
| `4000 0000 0000 3220` | Requires 3D Secure |

- Expiry: Any future date (e.g., `12/28`)
- CVC: Any 3 digits (e.g., `123`)

---

## 📍 New Routes

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/pricing` | GET | No | Pricing plans page |
| `/create-checkout-session` | POST | Yes | Creates Stripe checkout |
| `/subscription/success` | GET | Yes | Post-checkout success page |
| `/subscription/cancel` | GET | No | Redirect on checkout cancel |
| `/manage-subscription` | GET | Yes | View/cancel subscription |
| `/cancel-subscription` | POST | Yes | Cancel active subscription |
| `/webhook/stripe` | POST | No | Stripe webhook events |

---

## 🖼️ UI Changes

### Navigation Bar
- **★ Premium** link visible to all users
- User dropdown shows **★ PREMIUM** badge for subscribers
- Dropdown includes "Go Premium" / "Manage Plan" link

### Homepage
- **"Go Premium" CTA section** below hero for non-premium users
- **"You're on Premium!" banner** for subscribers

### Listings Page
- **Search limit banner** when free renters hit 5/day limit
- **★ Premium** badge on listings from premium owners
- Premium listings sort first in results

### Listing Detail
- **"Premium Owner"** badge on verified listings
- **Transaction fee estimate** shown below price

### Pricing Page (`/pricing`)
- 3-tier comparison (Free, Owner Premium, Renter Premium)
- Featured "Most Popular" card with CTA
- Transaction fee explainer section
- FAQ section

---

## 💻 Key Code Changes

### Models (`models.py`)
```python
# User subscription fields
subscription_tier     # 'free' or 'premium'
stripe_customer_id    # Stripe customer reference
stripe_subscription_id # Stripe subscription reference
subscription_expires  # Expiry datetime
search_count_today    # Daily search counter (renters)
search_reset_date     # When to reset counter

# Listing
is_premium_listing    # Priority placement flag
```

### Routes (`routes.py`)
```python
# Plan definitions
OWNER_PLAN   = { price: 999, ... }   # $9.99
RENTER_PLAN  = { price: 699, ... }   # $6.99
TRANSACTION_FEE_PERCENT = 8

# Helper functions
check_search_limit()   # Returns False if free renter exceeded 5/day
check_listing_limit()  # Returns False if free owner has 1+ active listing
```

---

## ⚠️ Important Notes

1. **Test Mode Only**: Stripe is in test mode. No real charges will be made.
2. **SQLite Limitation**: On Render free tier, the SQLite database resets on each deploy. Subscription status will be lost. For production, switch to PostgreSQL.
3. **Webhook Setup**: For production, set up a webhook endpoint in Stripe Dashboard pointing to `https://your-domain.com/webhook/stripe` and add the `STRIPE_WEBHOOK_SECRET` env var.
4. **Demo Mode**: If Stripe keys are not set, the subscription page still works — it activates premium immediately without payment (demo mode).

---

## 🧪 Testing Checklist

- [ ] Visit `/pricing` — see all 3 tiers
- [ ] Click "Subscribe" → redirected to Stripe Checkout
- [ ] Complete test payment with `4242 4242 4242 4242`
- [ ] Redirected to success page with features listed
- [ ] Profile dropdown shows ★ PREMIUM badge
- [ ] Homepage shows "You're on Premium!" banner
- [ ] Can post unlimited listings (if owner)
- [ ] Searches not rate-limited (if renter)
- [ ] Listings show "Premium Owner" badge
- [ ] `/manage-subscription` shows plan details
- [ ] Cancel subscription → reverts to free
- [ ] Listing detail shows 8% fee estimate

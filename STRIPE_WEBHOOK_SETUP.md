# Stripe Webhook Setup for Cancel Subscription

## Overview

The cancel subscription now uses **Stripe Customer Portal** with **webhook callbacks** for a better user experience:

1. User clicks cancel → Opens Stripe Customer Portal
2. User cancels in Stripe UI
3. Stripe sends webhook event `customer.subscription.updated`
4. Bot processes webhook and notifies user in Telegram

## Changes Made

### 1. Updated Cancel Flow (telegram_bot.py)

**Before:** Direct API cancellation
```python
stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
```

**After:** Stripe Customer Portal
```python
portal_session = stripe.billing_portal.Session.create(
    customer=stripe_customer_id,
    return_url='...'
)
# User opens portal URL, cancels there
```

### 2. Added Webhook Handler (payment_server.py)

**New endpoint:** `POST /webhook/stripe`

**Handles events:**
- `customer.subscription.updated` - Cancellation or reactivation
- `customer.subscription.deleted` - Immediate deletion

**Actions:**
- Updates local database (`subscription_active = false`)
- Sends Telegram notification to user
- Logs cancellation timestamp

## Setup Instructions

### Step 1: Add Webhook Secret to .env

```bash
# Add to .env file
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

**Get webhook secret:**
1. Go to Stripe Dashboard → Developers → Webhooks
2. Create endpoint or view existing one
3. Copy "Signing secret" (starts with `whsec_`)

### Step 2: Configure Stripe Webhook Endpoint

**If running locally (testing):**
1. Use Stripe CLI to forward webhooks:
   ```bash
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```

2. This gives you a webhook secret like:
   ```
   whsec_xxxxxxxxxxxxx
   ```

3. Add to `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
   ```

**If deployed to production:**
1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. URL: `https://your-domain.com/webhook/stripe`
4. Events to send:
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
5. Copy signing secret to `.env`

### Step 3: Enable Stripe Customer Portal

1. Go to Stripe Dashboard → Settings → Customer Portal
2. Enable customer portal
3. Configure settings:
   - ✅ Allow customers to cancel subscriptions
   - ✅ Show cancellation options
   - ✅ Set cancellation behavior: "Cancel at end of billing period"

### Step 4: Start Payment Server

```bash
python payment_server.py
```

**Output:**
```
Payment server starting on port 5000...
Success URL: http://localhost:5000/payment/success
Cancel URL: http://localhost:5000/payment/cancel
Webhook URL: http://localhost:5000/webhook/stripe
```

### Step 5: Test the Flow

1. **In Telegram bot:**
   ```
   /cancelsubscription
   ```

2. **Expected response:**
   ```
   😢 We're sorry to see you go!

   Are you sure you want to cancel your subscription?

   [❌ Yes, cancel my subscription]
   [✅ Keep my subscription]
   ```

3. **Click "Yes, cancel":**
   ```
   🔐 Opening Stripe Customer Portal...

   👉 Click the button below to manage your subscription in Stripe.

   [🔗 Open Stripe Portal to Cancel]

   ⚠️ After canceling in Stripe, you'll receive a confirmation here.
   🔔 We'll notify you once Stripe confirms the cancellation (usually instant).
   ```

4. **Click portal link:**
   - Opens Stripe Customer Portal
   - User sees subscription details
   - User clicks "Cancel subscription"
   - Confirms cancellation in Stripe

5. **Stripe sends webhook:**
   - Event: `customer.subscription.updated`
   - Data: `cancel_at_period_end = true`

6. **Bot receives notification (automatic):**
   ```
   ✅ Subscription Cancelled Successfully

   Your subscription has been cancelled in Stripe.

   📅 Access continues until: March 16, 2026

   You won't be charged again.

   Changed your mind? You can resubscribe anytime with /start

   Thank you for using LinkedInGrowthBot! 💙
   ```

## Flow Diagram

```
User: /cancelsubscription
  ↓
Bot: "Are you sure?"
  ↓
User: "Yes, cancel"
  ↓
Bot: Creates Stripe portal session
  ↓
Bot: Sends portal URL as inline button
  ↓
User: Clicks "Open Stripe Portal"
  ↓
Opens: https://billing.stripe.com/session/...
  ↓
User: Cancels subscription in Stripe UI
  ↓
Stripe: Sends webhook → POST /webhook/stripe
  ↓
Webhook handler:
  - Receives customer.subscription.updated
  - Checks: cancel_at_period_end = true
  - Updates: subscription_active = false
  - Sends: Telegram notification
  ↓
User: Receives confirmation in Telegram ✅
```

## Webhook Event Structure

### customer.subscription.updated (Cancellation)

```json
{
  "type": "customer.subscription.updated",
  "data": {
    "object": {
      "id": "sub_xxxxx",
      "customer": "cus_xxxxx",
      "status": "active",
      "cancel_at_period_end": true,
      "current_period_end": 1741305600,
      "cancel_at": 1741305600
    }
  }
}
```

**Handler logic:**
```python
if subscription['cancel_at_period_end']:
    # User cancelled subscription
    db.deactivate_subscription(telegram_id)
    send_telegram_notification("✅ Cancelled successfully")
```

### customer.subscription.deleted (Immediate)

```json
{
  "type": "customer.subscription.deleted",
  "data": {
    "object": {
      "id": "sub_xxxxx",
      "customer": "cus_xxxxx",
      "status": "canceled"
    }
  }
}
```

**Handler logic:**
```python
# Subscription ended immediately
db.deactivate_subscription(telegram_id)
send_telegram_notification("❌ Subscription ended")
```

## Troubleshooting

### Issue 1: "No Stripe customer ID found"

**Error:**
```
⚠️ Error: No Stripe customer ID found.
```

**Cause:** User doesn't have `stripe_customer_id` in database

**Fix:**
```sql
UPDATE users
SET stripe_customer_id = 'cus_xxxxx'
WHERE telegram_id = YOUR_ID;
```

### Issue 2: Webhook not received

**Symptoms:**
- User cancels in portal
- No Telegram notification received

**Checks:**
1. **Webhook endpoint accessible:**
   ```bash
   curl -X POST http://localhost:5000/webhook/stripe
   ```

2. **Stripe CLI forwarding:**
   ```bash
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```

3. **Check webhook logs:**
   - Stripe Dashboard → Developers → Webhooks → View logs
   - Look for failed deliveries

4. **Verify webhook secret:**
   ```bash
   echo $STRIPE_WEBHOOK_SECRET
   # Should start with whsec_
   ```

### Issue 3: Invalid signature

**Error in logs:**
```
Invalid signature
```

**Cause:** Wrong webhook secret

**Fix:**
1. Get correct secret from Stripe dashboard
2. Update `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_correct_secret_here
   ```
3. Restart payment server

### Issue 4: User not found in webhook

**Error in logs:**
```
User not found for customer cus_xxxxx
```

**Cause:** Database doesn't have matching `stripe_customer_id`

**Fix:**
```sql
UPDATE users
SET stripe_customer_id = 'cus_xxxxx',
    stripe_subscription_id = 'sub_xxxxx'
WHERE telegram_id = YOUR_ID;
```

## Testing Webhook Locally

### Using Stripe CLI (Recommended)

1. **Install Stripe CLI:**
   ```bash
   # Windows
   scoop install stripe

   # Or download from: https://stripe.com/docs/stripe-cli
   ```

2. **Login:**
   ```bash
   stripe login
   ```

3. **Forward webhooks:**
   ```bash
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```

4. **Trigger test event:**
   ```bash
   stripe trigger customer.subscription.updated
   ```

5. **Check payment server logs:**
   ```
   Received Stripe event: customer.subscription.updated
   Subscription updated: sub_xxxxx, cancel_at_period_end=True
   Notification sent to user 123456789
   ```

### Manual Testing

1. **Create test subscription in Stripe:**
   - Use test mode
   - Card: 4242 4242 4242 4242

2. **Cancel in portal:**
   - Open customer portal
   - Cancel subscription

3. **Watch logs:**
   ```bash
   # Payment server logs
   tail -f payment_server.log

   # Stripe CLI logs
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```

## Production Deployment

### Webhook URL

**Production URL:** `https://your-domain.com/webhook/stripe`

### Setup Steps

1. **Deploy payment server:**
   ```bash
   # On production server
   python payment_server.py
   # Or use gunicorn
   gunicorn payment_server:app --bind 0.0.0.0:5000
   ```

2. **Add to Stripe:**
   - Stripe Dashboard → Webhooks → Add endpoint
   - URL: `https://your-domain.com/webhook/stripe`
   - Events: `customer.subscription.updated`, `customer.subscription.deleted`

3. **Update .env:**
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_production_secret
   PAYMENT_SERVER_URL=https://your-domain.com
   ```

4. **Test:**
   - Send test webhook from Stripe dashboard
   - Check logs for "Received Stripe event"

## Benefits of New Flow

1. **Transparent** - User sees Stripe's official cancellation UI
2. **Reliable** - Webhook ensures cancellation is confirmed
3. **Professional** - Uses Stripe Customer Portal (best practice)
4. **Flexible** - User can also update payment method, view history
5. **Traceable** - Webhook events logged in Stripe dashboard

## Rollback Plan

If webhook flow has issues, temporarily revert to direct API:

```python
# In telegram_bot.py, line 1791
# Comment out portal code, uncomment:
subscription = stripe.Subscription.modify(
    stripe_subscription_id,
    cancel_at_period_end=True
)
```

---

**Status:** ✅ Implemented - Ready for webhook configuration

**Next Steps:**
1. Set up Stripe webhook endpoint
2. Test with Stripe CLI
3. Deploy to production

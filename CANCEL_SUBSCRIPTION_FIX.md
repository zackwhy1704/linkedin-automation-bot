# Cancel Subscription - Diagnostic & Fix Guide

## Problem

The `/cancelsubscription` command is "not picking up the subscription" - likely one of these issues:

1. ❌ User doesn't exist in database
2. ❌ `subscription_active` is FALSE
3. ❌ `stripe_subscription_id` is NULL/missing
4. ❌ Stripe subscription ID is invalid

## Quick Diagnosis

### Step 1: List All Users

```bash
python test_cancel_subscription.py list
```

**Output shows:**
- All users in database
- Their subscription status (✅/❌)
- Stripe subscription ID
- Expiration dates

### Step 2: Test Specific User

```bash
python test_cancel_subscription.py test YOUR_TELEGRAM_ID
```

**Example:**
```bash
python test_cancel_subscription.py test 123456789
```

**This checks:**
1. ✅ User exists
2. ✅ Subscription is active
3. ✅ Stripe subscription ID is present
4. ✅ Stripe subscription is valid
5. ✅ Cancellation would succeed

## Common Issues & Fixes

### Issue 1: "Subscription is not active"

**Error in bot:**
```
❌ You don't have an active subscription.

Send /start to subscribe.
```

**Cause:** `subscription_active = false` in database

**Fix Option A - Activate via Payment:**
1. In Telegram bot, send `/start`
2. Complete Stripe payment
3. Webhook activates subscription

**Fix Option B - Manual Activation (Testing):**
```bash
python test_cancel_subscription.py activate YOUR_TELEGRAM_ID
```

Or via SQL:
```sql
UPDATE users
SET subscription_active = true,
    subscription_expires = NOW() + INTERVAL '30 days'
WHERE telegram_id = YOUR_TELEGRAM_ID;
```

### Issue 2: "No Stripe subscription ID found"

**Error in bot:**
```
⚠️ No Stripe subscription found.

Your subscription may have been created manually. Contact support for assistance.
```

**Cause:** `stripe_subscription_id` is NULL

**Fix Option A - Get from Stripe Dashboard:**
1. Go to Stripe Dashboard → Subscriptions
2. Find the subscription for this user
3. Copy subscription ID (starts with `sub_`)
4. Update database:
   ```sql
   UPDATE users
   SET stripe_subscription_id = 'sub_xxxxxxxxxxxxx'
   WHERE telegram_id = YOUR_TELEGRAM_ID;
   ```

**Fix Option B - Manual for Testing:**
```bash
python test_cancel_subscription.py activate YOUR_TELEGRAM_ID sub_test123
```

### Issue 3: Stripe Subscription Doesn't Exist

**Error in diagnostic:**
```
❌ ERROR: Stripe subscription not found
   Error: No such subscription: 'sub_xxxxx'
```

**Cause:** Subscription ID in database doesn't match any subscription in Stripe

**Fix:**
1. Remove invalid ID:
   ```sql
   UPDATE users
   SET stripe_subscription_id = NULL
   WHERE telegram_id = YOUR_TELEGRAM_ID;
   ```

2. Create new subscription via bot: `/start` → Pay

## Testing the Fix

### Test Full Flow:

1. **List users:**
   ```bash
   python test_cancel_subscription.py list
   ```

2. **Activate test subscription:**
   ```bash
   python test_cancel_subscription.py activate 123456789 sub_test123
   ```

3. **Test cancellation:**
   ```bash
   python test_cancel_subscription.py test 123456789
   ```

4. **In Telegram bot:**
   ```
   /cancelsubscription
   ```

   Should show:
   ```
   😢 We're sorry to see you go!

   Are you sure you want to cancel your subscription?

   ⚠️ You will lose access to:
   • AI-generated posts
   • Smart feed engagement
   • Automated networking
   • Analytics dashboard

   Your subscription will remain active until the end of your current billing period.

   [❌ Yes, cancel my subscription]
   [✅ Keep my subscription]
   ```

5. **Click "Yes, cancel"**

   Should show:
   ```
   ✅ Subscription Cancelled

   Your subscription has been successfully cancelled in Stripe.

   📅 Access continues until: March 16, 2026

   You won't be charged again.

   Changed your mind? You can resubscribe anytime with /start

   Thank you for using LinkedInGrowthBot! 💙
   ```

## For Production Users

### Real Stripe Subscription

If user paid via Stripe but can't cancel:

1. **Check database:**
   ```sql
   SELECT
       telegram_id,
       username,
       subscription_active,
       stripe_subscription_id,
       stripe_customer_id
   FROM users
   WHERE telegram_id = YOUR_TELEGRAM_ID;
   ```

2. **Check Stripe dashboard:**
   - Go to Customers
   - Search by email or telegram_id
   - Find their subscription
   - Note the subscription ID

3. **Update database if missing:**
   ```sql
   UPDATE users
   SET stripe_subscription_id = 'sub_xxxxxxxxxxxxx'
   WHERE telegram_id = YOUR_TELEGRAM_ID;
   ```

4. **Test again:**
   ```bash
   python test_cancel_subscription.py test YOUR_TELEGRAM_ID
   ```

## How Cancel Subscription Works

### User Flow:
```
User: /cancelsubscription
  ↓
Bot checks: subscription_active = true?
  ↓ NO → "You don't have an active subscription"
  ↓ YES
  ↓
Bot checks: stripe_subscription_id exists?
  ↓ NO → "No Stripe subscription found"
  ↓ YES
  ↓
Show confirmation dialog
  ↓
User clicks: "Yes, cancel my subscription"
  ↓
Call: stripe.Subscription.modify(id, cancel_at_period_end=True)
  ↓
Call: db.deactivate_subscription(telegram_id)
  ↓
Show: "✅ Subscription Cancelled. Access until: [date]"
```

### Code Path:

**File:** [telegram_bot.py:1733](telegram_bot.py#L1733)

```python
async def cancel_subscription_command(update, context):
    # Check 1: Subscription active
    if not db.is_subscription_active(telegram_id):
        return "❌ You don't have an active subscription"

    # Check 2: Stripe subscription ID
    user_data = db.get_user(telegram_id)
    stripe_subscription_id = user_data.get('stripe_subscription_id')

    if not stripe_subscription_id:
        return "⚠️ No Stripe subscription found"

    # Show confirmation dialog
    ...
```

## Database Schema Reference

**users table:**
```sql
telegram_id              BIGINT PRIMARY KEY
subscription_active      BOOLEAN DEFAULT FALSE
subscription_expires     TIMESTAMP WITH TIME ZONE
stripe_subscription_id   VARCHAR(255)
stripe_customer_id       VARCHAR(255)
```

**Required for cancel to work:**
- ✅ `subscription_active = true`
- ✅ `stripe_subscription_id != NULL`
- ✅ Valid subscription in Stripe

## Troubleshooting Checklist

When user reports "cancel not working":

- [ ] Run: `python test_cancel_subscription.py list`
- [ ] Verify user exists in output
- [ ] Check `Active` column shows `✅ Yes`
- [ ] Check `Stripe ID` column shows valid ID (not "None")
- [ ] Run: `python test_cancel_subscription.py test <telegram_id>`
- [ ] All 5 checks should pass ✅
- [ ] Test `/cancelsubscription` in bot
- [ ] If still fails, check logs for specific error

## Quick Fixes for Testing

**Create test user with active subscription:**
```bash
# Create/activate test subscription
python test_cancel_subscription.py activate YOUR_TELEGRAM_ID sub_test123

# Test it works
python test_cancel_subscription.py test YOUR_TELEGRAM_ID

# Try in bot
/cancelsubscription
```

**Reset user subscription:**
```sql
UPDATE users
SET
    subscription_active = false,
    stripe_subscription_id = NULL,
    subscription_expires = NULL
WHERE telegram_id = YOUR_TELEGRAM_ID;
```

## Success Criteria

✅ **Cancellation works when:**

1. User runs `/cancelsubscription`
2. Bot shows confirmation dialog
3. User clicks "Yes, cancel"
4. Bot shows success message with expiration date
5. Database updated: `subscription_active = false`
6. Stripe subscription marked: `cancel_at_period_end = true`

---

**Status:** Diagnostic tool ready at [test_cancel_subscription.py](test_cancel_subscription.py)

**Next Step:** Run `python test_cancel_subscription.py list` to see current user states

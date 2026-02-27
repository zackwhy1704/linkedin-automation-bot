# Cancel Subscription - Portal + Direct API Fallback

## Implementation

The cancel subscription now offers **both portal and direct API options** with intelligent fallback logic.

### Flow Options

**Scenario 1: Portal Available (Ideal)**
```
User confirms cancel
  ↓
Show 2 options:
  [🔗 Open Stripe Portal (Recommended)]
  [⚡ Direct API Cancel (Fallback)]
```

**Scenario 2: Portal Fails**
```
User confirms cancel
  ↓
Try to create portal → FAILS
  ↓
Show only:
  [⚡ Cancel via Direct API]
```

**Scenario 3: No Customer ID**
```
User confirms cancel
  ↓
No stripe_customer_id in database
  ↓
Show only:
  [⚡ Cancel via Direct API]
```

## User Experience

### Path 1: Stripe Portal (Recommended)

**Step 1: Initial prompt**
```
/cancelsubscription

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

**Step 2: Choose method**
```
🔐 Choose cancellation method:

✅ **Recommended: Stripe Portal**
• Official Stripe interface
• Webhook confirmation
• Update payment method
• View billing history

⚡ **Fallback: Direct API**
• Immediate cancellation
• No webhook needed
• Use if portal fails

⚠️ After canceling in portal, you'll receive webhook confirmation.

[🔗 Open Stripe Portal (Recommended)]
[⚡ Direct API Cancel (Fallback)]
```

**Step 3a: User clicks portal**
- Opens Stripe Customer Portal
- Cancels in official Stripe UI
- Webhook sent to bot
- User receives confirmation automatically

**Step 3b: User clicks direct API**
```
✅ Subscription Cancelled via Direct API

Your subscription has been successfully cancelled in Stripe.

📅 Access continues until: March 16, 2026

You won't be charged again.

Changed your mind? You can resubscribe anytime with /start

Thank you for using LinkedInGrowthBot! 💙
```

### Path 2: Portal Unavailable (Fallback Only)

**Portal creation fails:**
```
⚠️ Stripe Portal unavailable:

No such customer: 'cus_xxxxx'

Using direct API cancellation instead:

👇 Click below to cancel your subscription immediately.

[⚡ Cancel via Direct API]
```

**No customer ID in database:**
```
ℹ️ No customer portal available.

Using direct API cancellation:

⚡ This will immediately cancel your subscription via Stripe API.

👇 Click below to proceed:

[⚡ Cancel via Direct API]
```

## Code Logic

### Callback Handler Structure

```python
async def handle_cancel_subscription_callback(update, context):
    if query.data == 'keep_sub':
        # User changed mind
        return

    if query.data == 'confirm_cancel_sub':
        # Step 1: Try portal (if customer_id exists)
        if stripe_customer_id:
            try:
                portal_session = stripe.billing_portal.Session.create(...)
                # Show: Portal + Fallback API buttons
            except stripe.error.StripeError:
                # Portal failed
                # Show: Only Fallback API button
        else:
            # No customer ID
            # Show: Only Fallback API button

    elif query.data == 'force_cancel_sub':
        # Step 2: Direct API cancellation
        subscription = stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
        # Update database
        # Show confirmation
```

### Decision Tree

```
confirm_cancel_sub pressed
  ↓
Has stripe_customer_id?
  ↓ YES                     ↓ NO
  ↓                         ↓
Try create portal           Has subscription_id?
  ↓                           ↓ YES        ↓ NO
  ↓ SUCCESS    ↓ FAIL         ↓            ↓
  ↓            ↓              ↓            Error
Show both    Show API       Show API
options      only           only
```

## Fallback Reasons

**When fallback API is used:**

1. **Portal creation fails** - Stripe error creating portal session
2. **No customer ID** - Missing `stripe_customer_id` in database
3. **User preference** - User chooses direct API even when portal available
4. **Webhook issues** - User doesn't want to wait for webhook

**Benefits of fallback:**
- ✅ Always works (if subscription ID exists)
- ✅ Instant confirmation (no webhook wait)
- ✅ Simple implementation
- ✅ Works offline/without portal enabled

**Drawbacks of fallback:**
- ❌ No Stripe UI for user
- ❌ No payment method update option
- ❌ No billing history view
- ❌ Less "official" feel

## Error Handling

### No Subscription ID

```python
if not stripe_subscription_id:
    await query.edit_message_text(
        "❌ Error: No Stripe subscription ID found.\n\n"
        "Cannot cancel - subscription ID missing from database."
    )
```

### Invalid Subscription

```python
except stripe.error.InvalidRequestError as e:
    # Subscription doesn't exist in Stripe
    await query.edit_message_text(
        f"❌ Stripe API Error:\n\n{str(e)}\n\n"
        "The subscription may not exist or is already cancelled."
    )
```

### General Stripe Error

```python
except stripe.error.StripeError as e:
    await query.edit_message_text(
        f"❌ Error cancelling subscription:\n\n{str(e)}"
    )
```

## Testing

### Test Case 1: Both Options Available

**Setup:**
```sql
UPDATE users SET
    stripe_customer_id = 'cus_test123',
    stripe_subscription_id = 'sub_test123'
WHERE telegram_id = YOUR_ID;
```

**Test:**
```
/cancelsubscription → Yes → See both buttons
```

### Test Case 2: Portal Fails, Fallback Works

**Setup:** Use invalid customer ID
```sql
UPDATE users SET
    stripe_customer_id = 'cus_invalid',
    stripe_subscription_id = 'sub_valid123'
WHERE telegram_id = YOUR_ID;
```

**Test:**
```
/cancelsubscription → Yes → See only API button (portal failed)
```

### Test Case 3: Only API Available

**Setup:** No customer ID
```sql
UPDATE users SET
    stripe_customer_id = NULL,
    stripe_subscription_id = 'sub_test123'
WHERE telegram_id = YOUR_ID;
```

**Test:**
```
/cancelsubscription → Yes → See only API button
```

### Test Case 4: Both Fail

**Setup:** No IDs
```sql
UPDATE users SET
    stripe_customer_id = NULL,
    stripe_subscription_id = NULL
WHERE telegram_id = YOUR_ID;
```

**Test:**
```
/cancelsubscription → Error: No Stripe data found
```

## Callback Handler Pattern

**Updated pattern includes fallback:**
```python
application.add_handler(CallbackQueryHandler(
    handle_cancel_subscription_callback,
    pattern='^(confirm_cancel_sub|keep_sub|force_cancel_sub)$'
))
```

## Files Modified

1. **telegram_bot.py:1791** - Added fallback logic
2. **telegram_bot.py:1992** - Updated callback pattern

## Summary

### What Changed

**Before:**
- Portal only (if customer ID exists)
- Error if portal fails
- No fallback option

**After:**
- Portal + Fallback (intelligent)
- Fallback API if portal fails
- Fallback API if no customer ID
- User can choose either method

### Benefits

1. **Always Works** - Fallback ensures cancellation succeeds
2. **User Choice** - User decides portal vs API
3. **Handles Errors** - Graceful fallback on portal failure
4. **Database Agnostic** - Works even if customer_id missing
5. **Instant Option** - Direct API for immediate cancellation

### When Each Method is Used

**Portal (Recommended):**
- Customer ID exists
- Portal creation succeeds
- User wants official Stripe UI
- User clicks "Open Stripe Portal"

**Direct API (Fallback):**
- Portal creation fails
- No customer ID in database
- User prefers instant cancellation
- User clicks "Direct API Cancel"

---

**Status:** ✅ Implemented with intelligent fallback

**Test:** `/cancelsubscription` → See both options (or fallback only if portal unavailable)

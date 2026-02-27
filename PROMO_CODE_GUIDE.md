# 🎁 Promo Code Setup Guide

How to add and use promo codes in your Telegram bot.

---

## 📋 Quick Setup

### Step 1: Create Promo Codes

Run this script once:

```bash
python create_promo_codes.py
```

This creates:
- **FREETRIAL** - 1-day free trial
- **LAUNCH50** - 50% off for 30 days
- **WEEK50** - 50% off for 1 week

---

## 🎯 How It Works

### User Flow with FREETRIAL:

1. User completes profile setup
2. Gets to payment screen
3. Clicks "🎁 I have a promo code"
4. Enters: `FREETRIAL`
5. Bot responds:
   ```
   🎉 FREETRIAL applied!
   
   ✅ You have a FREE 1-day trial!
   
   What happens next:
   • Full access for 24 hours (starting now)
   • After 1 day, you'll be charged $0.99/day
   • Cancel anytime via /cancel
   
   Your trial is active! Send /autopilot to start automating. 🚀
   ```

6. User can use bot for 24 hours
7. After 24 hours, subscription expires
8. User needs to subscribe to continue

---

## 💡 Promo Code Types

### Free Trial (100% off)

```python
db.create_promo_code(
    code='FREETRIAL',
    discount_percent=100,  # 100% = free
    max_uses=1000,         # 1000 people can use it
    days_valid=365         # Code valid for 1 year
)
```

**What happens:**
- User gets immediate access
- No payment required
- Access expires after X days (you set this)
- No auto-billing after trial

**Best for:**
- Getting users to try the product
- Testing conversion rates
- Limited-time promotions

---

## 🔧 Customizing Trial Duration

**Want a 3-day trial instead of 1 day?**

Edit `telegram_bot.py` line ~320:

```python
# Change this:
db.activate_subscription(telegram_id, days=1)

# To this:
db.activate_subscription(telegram_id, days=3)
```

Or create different codes:

```python
# 1-day trial
db.create_promo_code('TRIAL1DAY', 100, 500, 365)

# 3-day trial  
db.create_promo_code('TRIAL3DAY', 100, 300, 365)

# 7-day trial
db.create_promo_code('TRIAL7DAY', 100, 100, 365)
```

Then update the handler to check which code was used.

---

## 📊 Tracking Promo Code Usage

**See how many people used a code:**

```python
from bot_database import BotDatabase
db = BotDatabase()

result = db.validate_promo_code('FREETRIAL')
print(f"Uses: {result['current_uses']} / {result['max_uses']}")
```

**List all promo codes:**

```bash
sqlite3 data/telegram_bot.db "SELECT code, current_uses, max_uses FROM promo_codes;"
```

---

## 🎨 Custom Promo Codes

### Launch Weekend (50% off)

```python
db.create_promo_code(
    code='LAUNCH50',
    discount_percent=50,
    max_uses=100,
    days_valid=3  # Valid for 3 days only
)
```

### Influencer Codes

```python
# Give each influencer a unique code
db.create_promo_code('JOHN50', 50, 50, 30)
db.create_promo_code('SARAH50', 50, 50, 30)
db.create_promo_code('MIKE50', 50, 50, 30)
```

Track which influencer drives most signups!

### VIP Code (100 uses only)

```python
db.create_promo_code('VIP100', 100, 100, 365)
```

---

## 🚨 Important Notes

### Free Trials Don't Auto-Convert

Current implementation:
- User gets X days free
- After X days, access expires
- User must manually subscribe to continue

**If you want auto-conversion** (trial → paid), you need to use Stripe's trial feature instead. See below.

---

## 🔄 Auto-Converting Trials (Advanced)

For trials that automatically convert to paid:

```python
# In handle_subscription function, add trial_period_days:

session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    line_items=[{
        'price': STRIPE_PRICE_ID,
        'quantity': 1,
    }],
    mode='subscription',
    subscription_data={
        'trial_period_days': 1,  # 1-day trial before first charge
    },
    # ... rest of config
)
```

**This way:**
1. User enters card info
2. Not charged for 1 day (trial)
3. After 1 day, automatically charged $0.99/day
4. No manual intervention needed

---

## ✅ Testing Promo Codes

1. Create test code:
   ```bash
   python create_promo_codes.py
   ```

2. Start bot:
   ```bash
   python telegram_bot.py
   ```

3. Send `/start` to bot
4. Complete profile
5. Click "🎁 I have a promo code"
6. Enter `FREETRIAL`
7. Verify you get confirmation message
8. Check database:
   ```bash
   sqlite3 data/telegram_bot.db "SELECT * FROM users;"
   ```
9. Verify `subscription_active = 1`

---

## 🎉 Promo Code Ideas

| Code | Purpose | Discount | Duration |
|------|---------|----------|----------|
| FREETRIAL | New user acquisition | 100% | 1 day |
| EARLYBIRD | Launch promotion | 50% | 7 days |
| FRIEND50 | Referral program | 50% | 30 days |
| LAUNCH | Grand opening | 100% | 3 days |
| SAVE20 | Regular discount | 20% | Ongoing |

---

You're all set! Users can now use **FREETRIAL** for instant 1-day access. 🚀

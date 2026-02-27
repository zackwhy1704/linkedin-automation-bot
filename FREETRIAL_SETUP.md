# 🎁 FREETRIAL Promo Code Setup

Complete guide for $0.00 checkout with auto-conversion after 24 hours.

---

## 🎯 User Experience

### What Users See:

```
User: /start
Bot: [Profile setup questions]
User: [Completes profile]
Bot: 💎 Premium Access - Just $0.99/day
     [💳 Subscribe] [🎁 Promo code]

User: *clicks promo code*
Bot: 🎁 Enter your promo code:
     Try: FREETRIAL (1-day free access)

User: FREETRIAL

Bot: 🎉 FREETRIAL Activated!
     
     ✅ You get a 1-DAY FREE TRIAL!
     
     How it works:
     1️⃣ Enter your card (secure with Stripe)
     2️⃣ You pay $0.00 today
     3️⃣ Get full access for 24 hours
     4️⃣ After 24 hours → auto-charged $0.99/day
     5️⃣ Cancel anytime (even during trial)
     
     💳 [Start 1-Day FREE Trial 🎁]

User: *clicks button*
→ Opens Stripe checkout page

Stripe: Total today: $0.00
        Starting Dec 16: $0.99/day

User: *enters card, completes checkout*
→ Returns to Telegram

User: /activate

Bot: 🎉 Subscription Activated!
     
     Your 24-hour FREE trial has started!
     Send /autopilot to begin automating.

[24 hours pass]

→ Stripe automatically charges $0.99
→ Daily billing continues until user cancels
```

---

## ⚙️ How It Works (Technical)

### Stripe Trial Period Feature

When user enters `FREETRIAL`:

1. **Creates Stripe checkout session** with:
   ```python
   subscription_data={
       'trial_period_days': 1,  # 1-day free trial
   }
   ```

2. **User completes checkout:**
   - Card is verified (but not charged)
   - Subscription created with trial period
   - Charge amount: **$0.00**

3. **Trial period (24 hours):**
   - User has full access
   - Card on file, ready to charge
   - Can cancel anytime

4. **After 24 hours:**
   - Stripe **automatically charges $0.99**
   - Daily billing begins
   - Continues until user cancels

---

## 🚀 Setup Instructions

### Step 1: Create FREETRIAL Code

Run this once:

```bash
python create_promo_codes.py
```

This creates:
```python
db.create_promo_code(
    code='FREETRIAL',
    discount_percent=100,  # 100% = free trial
    max_uses=1000,
    days_valid=365
)
```

### Step 2: Restart Bot

```bash
python telegram_bot.py
```

### Step 3: Test the Flow

1. Message bot: `/start`
2. Complete profile
3. Click "🎁 I have a promo code"
4. Enter: `FREETRIAL`
5. Click "Start 1-Day FREE Trial"
6. Enter test card: `4242 4242 4242 4242`
7. Complete checkout (shows $0.00)
8. Return to Telegram
9. Send `/activate`
10. Verify trial is active
11. Wait 24 hours (or check Stripe Dashboard)
12. Verify first charge of $0.99 occurs

---

## 💳 Stripe Dashboard View

### During Trial (First 24 Hours)

```
Subscription Status: Active (trialing)
Trial ends: Dec 16, 2024 at 3:00 PM
Amount: $0.99/day (starts after trial)
Next charge: Dec 16, 2024 - $0.99
```

### After Trial Ends

```
Subscription Status: Active
Last charge: Dec 16, 2024 - $0.99
Next charge: Dec 17, 2024 - $0.99
Billing: Daily
```

---

## 📊 Revenue Impact

**Without trial:**
- Conversion rate: ~3-5%
- Out of 100 visitors: 3-5 subscribers

**With 1-day free trial:**
- Trial signup rate: ~15-25% (5x higher!)
- Trial → paid conversion: ~40-60%
- Net conversion: ~6-15% (2-3x higher!)

**Example:**
- 100 visitors
- 20 start trial (20%)
- 10 convert to paid (50% trial conversion)
- **Result: 10 subscribers vs 3 without trial**

---

## 🎯 Variations

### 3-Day Trial

```python
subscription_data={
    'trial_period_days': 3,
}
```

### 7-Day Trial

```python
subscription_data={
    'trial_period_days': 7,
}
```

### Different Trial Codes

```python
# 1-day trial
db.create_promo_code('TRIAL1', 100, 500, 365)

# 3-day trial
db.create_promo_code('TRIAL3', 100, 300, 365)

# 7-day trial
db.create_promo_code('TRIAL7', 100, 100, 365)
```

Update handler to check code and set different trial lengths:

```python
if promo_code == 'TRIAL1':
    trial_days = 1
elif promo_code == 'TRIAL3':
    trial_days = 3
elif promo_code == 'TRIAL7':
    trial_days = 7

subscription_data={'trial_period_days': trial_days}
```

---

## 🔔 Email Notifications (Stripe)

Users automatically receive:

**When trial starts:**
```
Subject: Your trial has started

Your 1-day trial for LinkedIn Growth Bot is now active!

Trial ends: Dec 16, 2024
After trial: $0.99/day

Cancel anytime: [Manage Subscription]
```

**3 days before trial ends (if 7+ day trial):**
```
Subject: Your trial ends soon

Your trial ends in 3 days.

Starting Dec 16: $0.99/day

Cancel before then to avoid charges.
```

**When first charge occurs:**
```
Subject: Receipt for $0.99

You were charged $0.99 for LinkedIn Growth Bot.

View receipt: [Link]
```

---

## 🚨 Cancellation During Trial

If user cancels **during trial**:

```
User: /cancel

Bot: Cancel your subscription?
     [Yes, cancel] [Keep subscription]

User: *clicks cancel*

→ Stripe cancels subscription
→ Trial ends immediately OR
→ Access until trial period ends (your choice)
→ No charge occurs
```

**Stripe setting:**
- Dashboard → Settings → Subscriptions
- "When customers cancel": 
  - ✅ End immediately (recommended)
  - ⚪ End at period end (let them finish trial)

---

## 📈 Optimization Tips

### Messaging Tests

**Option A: Emphasize $0 today**
```
You pay $0.00 today!
24 hours completely FREE.
```

**Option B: Emphasize low commitment**
```
Just $0.99/day after trial
Cancel anytime (even during trial)
```

**Option C: Social proof**
```
Join 1,000+ users growing on LinkedIn
Start FREE - no risk!
```

### Reduce Trial Abandonment

**During trial, send:**

**Day 1 (immediately):**
```
Welcome! Your trial started. 
Send /autopilot to see it work!
```

**12 hours in:**
```
📊 Your first 12 hours:
• 3 posts engaged
• 2 connection requests sent

Keep going! Send /autopilot again.
```

**20 hours in (before trial ends):**
```
⏰ Trial ends in 4 hours!

To keep your automation:
✅ Do nothing (auto-continues at $0.99/day)

To cancel:
Send /cancel
```

---

## ✅ Testing Checklist

Before launch:

- [ ] Created FREETRIAL promo code
- [ ] Tested full signup flow
- [ ] Verified Stripe shows $0.00 charge
- [ ] Confirmed trial period = 1 day
- [ ] Tested first charge occurs after 24hrs
- [ ] Verified cancellation during trial works
- [ ] Checked email notifications sent
- [ ] Tested /activate command
- [ ] Monitored trial → paid conversion rate

---

You're all set! Users can now try your bot **FREE for 24 hours** with `FREETRIAL`! 🎉

**Next step:** Market it as "Try FREE for 24 hours - No credit card required... wait, yes credit card required but $0 today!" 😄

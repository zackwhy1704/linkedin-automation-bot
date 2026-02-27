# 💳 Credit Card Payment Guide

Complete guide for accepting credit card payments via Stripe.

---

## ✅ Accepted Payment Methods

Your bot accepts **all major credit cards**:

- ✓ **Visa**
- ✓ **Mastercard** 
- ✓ **American Express**
- ✓ **Discover**
- ✓ **Diners Club**
- ✓ **JCB**
- ✓ **UnionPay**

Plus international cards from 135+ countries.

---

## 🔒 Security Features

✅ **PCI-DSS Compliant** — Stripe handles all card data, you never see card numbers
✅ **3D Secure** — Automatic verification for high-risk transactions  
✅ **Fraud Detection** — Stripe Radar prevents fraudulent charges
✅ **SSL Encryption** — All payment data encrypted in transit
✅ **No Storage** — Card details never stored on your server

---

## 🧪 Testing Credit Card Payments

### Test Cards (Stripe Test Mode)

**Successful Payment:**
```
Card Number:  4242 4242 4242 4242
Expiry:       Any future date (e.g., 12/34)
CVC:          Any 3 digits (e.g., 123)
ZIP:          Any 5 digits (e.g., 12345)
```

**Card Requires 3D Secure:**
```
Card Number:  4000 0027 6000 3184
```

**Payment Declined:**
```
Card Number:  4000 0000 0000 0002
```

**Insufficient Funds:**
```
Card Number:  4000 0000 0000 9995
```

**Full list:** https://stripe.com/docs/testing#cards

### How to Test

1. Make sure `.env` has `STRIPE_SECRET_KEY` starting with `sk_test_`
2. Run your bot: `python telegram_bot.py`
3. Send `/start` to your bot on Telegram
4. Complete profile setup
5. When prompted for payment, click "Pay with Credit Card"
6. Use test card: `4242 4242 4242 4242`
7. Complete the Stripe checkout form
8. Payment succeeds → subscription activated!

---

## 🌍 International Payments

Stripe automatically handles:

✅ **Currency Conversion** — Accept cards from any country
✅ **Local Payment Methods** — Alipay, WeChat Pay, SEPA, etc. (optional)
✅ **Multi-Currency** — Charge in USD, EUR, GBP, etc.
✅ **Tax Collection** — Automatic sales tax/VAT calculation

### Enable Additional Payment Methods

Edit `telegram_bot.py`:

```python
payment_method_types=['card', 'alipay', 'wechat_pay', 'link']
```

Available options:
- `card` — Credit/debit cards (default)
- `alipay` — Alipay (popular in China)
- `wechat_pay` — WeChat Pay
- `link` — Stripe Link (1-click checkout)
- `us_bank_account` — ACH Direct Debit (US only)
- See full list: https://stripe.com/docs/payments/payment-methods

---

## 💰 Pricing & Fees

**Stripe Fees:**
- **Standard:** 2.9% + $0.30 per transaction
- **International cards:** +1.5% additional
- **Currency conversion:** +1% additional

**Example:**
```
Your price:     $29.00
Stripe fee:     $1.14 (2.9% + $0.30)
You receive:    $27.86
```

**Monthly revenue (100 subscribers):**
```
Gross:          $2,900
Stripe fees:    $114
Server costs:   -$50
Net profit:     $2,736/month
```

---

## 🔄 Subscription Management

### How Recurring Billing Works

1. User pays $29 → subscription created
2. Every 30 days, Stripe automatically charges the card
3. If payment succeeds → subscription continues
4. If payment fails → Stripe retries 3 times over 2 weeks
5. After 3 failures → subscription cancelled, user notified

### Handle Payment Failures

Users can update their card via Stripe Customer Portal:

```python
# Add this command to your bot
async def update_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = db.get_user(telegram_id)
    
    if not user['stripe_customer_id']:
        await update.message.reply_text("No payment method on file.")
        return
    
    # Create Billing Portal session
    session = stripe.billing_portal.Session.create(
        customer=user['stripe_customer_id'],
        return_url=f'https://t.me/{context.bot.username}'
    )
    
    keyboard = [[InlineKeyboardButton("Update Card 💳", url=session.url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Click below to update your payment method:",
        reply_markup=reply_markup
    )
```

---

## 📊 Payment Analytics

Track your revenue in Stripe Dashboard:

1. **Dashboard → Payments** — See all transactions
2. **Reports → Balance** — Daily revenue breakdown
3. **Customers → Subscriptions** — MRR, churn rate
4. **Radar → Rules** — Fraud detection stats

---

## 🚨 Common Issues & Fixes

### "Payment Method Not Supported"

**Cause:** Using `sk_live_` key but haven't activated account  
**Fix:** Complete Stripe verification or use `sk_test_` for testing

### "Card Declined"

**Causes:**
- Insufficient funds
- Card reported stolen/lost
- Bank blocking international charges
- 3D Secure failed

**User fix:** Try a different card or contact their bank

### "Subscription Not Activating"

**Cause:** Webhook not configured (production only)  
**Fix:** Set up Stripe webhook endpoint (see main setup guide)

For testing, manually activate:
```python
db.activate_subscription(telegram_id=123456789, days=30)
```

---

## 🎯 Best Practices

✅ **Use webhooks in production** — Don't rely on redirect URLs  
✅ **Test thoroughly** — Use all test cards before going live  
✅ **Enable fraud protection** — Turn on Stripe Radar  
✅ **Set up email receipts** — Stripe sends automatic receipts  
✅ **Monitor failed payments** — Send reminders via bot  
✅ **Offer payment plans** — Weekly or yearly billing  
✅ **Show value first** — Offer 7-day free trial to reduce refunds

---

## 🔐 Going Live (Production)

**Checklist before accepting real payments:**

- [ ] Complete Stripe account verification (tax ID, bank account)
- [ ] Switch from `sk_test_` to `sk_live_` keys
- [ ] Set up webhook endpoint for production
- [ ] Enable Stripe Radar for fraud detection
- [ ] Test live mode with your own real card ($1 test charge)
- [ ] Set up refund policy in Stripe settings
- [ ] Enable email receipts
- [ ] Add customer support email
- [ ] Monitor Dashboard for first 24 hours

---

## 📧 Customer Support

**Common questions:**

**Q: Is my card information safe?**  
A: Yes, we use Stripe — the same payment processor used by Amazon, Google, and Spotify. Your card info is encrypted and never stored on our servers.

**Q: Can I cancel anytime?**  
A: Yes, send `/cancel_subscription` to the bot.

**Q: Do you store my credit card?**  
A: No, only Stripe stores your card. We never see your card number.

**Q: Will I be charged automatically?**  
A: Yes, $29/month until you cancel.

**Q: Can I get a refund?**  
A: Pro-rated refunds available within 7 days of purchase.

---

## 📝 Legal Requirements

Before accepting payments, ensure you have:

✅ **Terms of Service** — What users are buying  
✅ **Privacy Policy** — How you handle data  
✅ **Refund Policy** — 7-day, 30-day, or no refunds?  
✅ **Business Registration** — LLC, sole proprietorship, etc.  
✅ **Tax Compliance** — Collect sales tax/VAT if required

---

You're all set to accept credit card payments! 💳

For more help: https://stripe.com/docs

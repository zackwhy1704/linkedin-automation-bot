# 🔧 Telegram Bot .env Setup

Quick guide to complete your Telegram bot configuration.

---

## 📋 What You Need

Your `.env` file now has placeholders. Here's what to fill in:

### 1. TELEGRAM_BOT_TOKEN

**Get from @BotFather:**

1. Open Telegram
2. Search: `@BotFather`
3. Send: `/newbot`
4. Name: `LinkedInGrowthBot`
5. Username: `LinkedInGrowthBot_bot` (must end with _bot)
6. Copy the token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Paste in .env:**
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

---

### 2. STRIPE_SECRET_KEY

**Get from Stripe Dashboard:**

1. Go to: https://dashboard.stripe.com/test/apikeys
2. Find **Secret key** (starts with `sk_test_`)
3. Click "Reveal test key"
4. Copy it

**Paste in .env:**
```
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**For production (later):**
- Use: https://dashboard.stripe.com/apikeys
- Copy the **live** secret key (starts with `sk_live_`)

---

### 3. STRIPE_PRICE_ID (Most Important!)

You have Product ID: `prod_Tz4VKdBvzvsSNs`

But you need the **Price ID** for $0.99/day:

**How to find it:**

1. Go to: https://dashboard.stripe.com/test/products
2. Click on your product: `prod_Tz4VKdBvzvsSNs`
3. Under **Pricing**, look for the price with:
   - Amount: **$0.99**
   - Interval: **Daily**
4. Copy the **API ID** (starts with `price_`)

**Paste in .env:**
```
STRIPE_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Screenshot guide:**
```
Product: LinkedIn Bot Subscription
├─ Pricing
   ├─ $0.99 / day
   │  API ID: price_1234567890abcdef  ← Copy this!
   └─ Add another price
```

---

### 4. ENCRYPTION_KEY

**Generate it:**

Run this command:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Output looks like:**
```
XYz1234ABCabc567DEF890ghi123JKL456mno789PQR012stu345==
```

**Paste in .env:**
```
ENCRYPTION_KEY=XYz1234ABCabc567DEF890ghi123JKL456mno789PQR012stu345==
```

---

## ✅ Complete .env Example

```bash
# LinkedIn Credentials
LINKEDIN_EMAIL=your_email@gmail.com
LINKEDIN_PASSWORD=your_password

# AI Service
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Stripe Payment
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_ID=price_1xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Encryption
ENCRYPTION_KEY=XYz1234ABCabc567DEF890ghi123JKL456mno789PQR012stu345==

# Bot Config
HEADLESS=False
BROWSER=chrome
```

---

## 🚀 After Setting Up

1. **Install dependencies:**
   ```bash
   pip install -r telegram_bot_requirements.txt
   ```

2. **Generate encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Copy output to ENCRYPTION_KEY in .env

3. **Create promo codes:**
   ```bash
   python create_promo_codes.py
   ```

4. **Start bot:**
   ```bash
   python telegram_bot.py
   ```

5. **Test it:**
   - Open Telegram
   - Search for your bot
   - Send `/start`

---

## 🆘 Troubleshooting

**Bot doesn't respond:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Make sure bot is running: `python telegram_bot.py`

**Payment fails:**
- Check `STRIPE_PRICE_ID` is for $0.99/day (not product ID!)
- Use test card: `4242 4242 4242 4242`

**"Invalid encryption key":**
- Regenerate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Make sure no spaces before/after the key

---

You're almost there! Just need to:
1. Get Telegram bot token from @BotFather
2. Get Stripe Price ID (not product ID!)
3. Generate encryption key

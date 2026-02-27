# LinkedInGrowthBot - Telegram Bot Setup Guide

Complete guide to deploy your LinkedIn automation bot on Telegram with Stripe payments.

---

## 📋 Prerequisites

- Python 3.8+
- Telegram account
- Stripe account
- Server/VPS (recommended: DigitalOcean, Hetzner, AWS)

---

## 🚀 Step 1: Create Your Telegram Bot

### 1.1 Talk to BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Choose a name: `LinkedInGrowthBot`
4. Choose a username: `LinkedInGrowthBot` (must end with 'bot')
5. BotFather will give you a **BOT TOKEN** — save this!

### 1.2 Set Bot Image

1. Send `/setuserpic` to BotFather
2. Select your bot
3. Upload the LinkedIn icon image you provided

### 1.3 Set Bot Description

Send `/setdescription` to BotFather and paste:

```
Automate your LinkedIn success with our AI-powered bot. Schedule posts, engage authentically with comments and likes, send personalized messages, and grow your network—all on autopilot. Stay active, build relationships, and generate leads 24/7 without lifting a finger.
```

### 1.4 Set About Text

Send `/setabouttext` and paste:

```
AI-powered LinkedIn automation. Grow your network on autopilot.
```

### 1.5 Set Commands

Send `/setcommands` to BotFather and paste:

```
start - Get started with the bot
autopilot - Run full LinkedIn automation
post - Generate and post AI content
engage - Engage with LinkedIn feed
connect - Send connection requests
schedule - Schedule content
stats - View your analytics
settings - Update your profile
subscription - Manage subscription
help - Get help
cancel - Cancel current operation
```

---

## 💳 Step 2: Set Up Stripe

### 2.1 Create Stripe Account

1. Go to [stripe.com](https://stripe.com)
2. Sign up for an account
3. Complete business verification

### 2.2 Create a Product

1. Go to Stripe Dashboard → Products
2. Click "Add Product"
3. Name: `LinkedIn Growth Bot Subscription`
4. Price: `$29/month` (recurring)
5. Click "Save"
6. Copy the **Price ID** (starts with `price_...`)

### 2.3 Get API Keys

1. Go to Stripe Dashboard → Developers → API keys
2. Copy your **Secret Key** (starts with `sk_test_...` or `sk_live_...`)
3. Keep this secret!

### 2.4 Set Up Webhooks (Optional for production)

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/stripe-webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`

---

## ⚙️ Step 3: Configure Environment Variables

Create a `.env` file in your project directory:

```bash
# Telegram Bot Token (from BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PRICE_ID=price_your_price_id_here

# Encryption Key (generate one using command below)
ENCRYPTION_KEY=your_encryption_key_here

# Anthropic API (for AI features)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📦 Step 4: Install Dependencies

```bash
# Install Telegram bot requirements
pip install -r telegram_bot_requirements.txt

# Install main bot requirements
pip install -r requirements.txt
```

---

## 🏃 Step 5: Run the Bot Locally (Testing)

```bash
python telegram_bot.py
```

You should see:
```
INFO - LinkedInGrowthBot started!
```

Test it:
1. Open Telegram
2. Search for your bot username
3. Send `/start`
4. Go through the onboarding flow

---

## 🌐 Step 6: Deploy to Production

### Option A: Deploy to VPS (Recommended)

**Requirements:**
- Ubuntu 20.04+ server
- 2GB RAM minimum
- Python 3.8+

**Setup:**

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip git -y

# Install Chrome (for Selenium)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y

# Clone your repo
git clone https://github.com/yourusername/linkedin-automation-bot.git
cd linkedin-automation-bot

# Install requirements
pip3 install -r telegram_bot_requirements.txt
pip3 install -r requirements.txt

# Create .env file
nano .env
# Paste your environment variables, save with Ctrl+X, Y, Enter

# Run with nohup (keeps running after SSH disconnect)
nohup python3 telegram_bot.py > bot.log 2>&1 &

# Check logs
tail -f bot.log
```

### Option B: Deploy with Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

WORKDIR /app

COPY requirements.txt telegram_bot_requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r telegram_bot_requirements.txt

COPY . .

CMD ["python", "telegram_bot.py"]
```

Run with Docker:
```bash
docker build -t linkedin-bot .
docker run -d --env-file .env linkedin-bot
```

### Option C: Deploy to Heroku

```bash
# Install Heroku CLI
# Create Procfile
echo "bot: python telegram_bot.py" > Procfile

# Deploy
heroku login
heroku create your-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set STRIPE_SECRET_KEY=your_key
# ... set all other env vars

git push heroku main
```

---

## 🎯 Step 7: Create Promo Codes

To create promo codes for users:

```python
from bot_database import BotDatabase

db = BotDatabase()

# Create a 50% off code valid for 30 days, max 100 uses
db.create_promo_code(
    code='LAUNCH50',
    discount_percent=50,
    max_uses=100,
    days_valid=30
)

# Create a free trial code
db.create_promo_code(
    code='FREETRIAL',
    discount_percent=100,
    max_uses=50,
    days_valid=7
)
```

Users can enter these codes during signup.

---

## 🧪 Step 8: Testing the Full Flow

1. **User Onboarding:**
   - Send `/start` to your bot
   - Fill in profile information
   - Enter LinkedIn credentials
   - Proceed to payment

2. **Payment Testing (Stripe Test Mode):**
   - Use test card: `4242 4242 4242 4242`
   - Any future expiry date
   - Any 3-digit CVC
   - Any ZIP code

3. **Activate Subscription Manually (for testing):**
   ```python
   from bot_database import BotDatabase
   db = BotDatabase()
   db.activate_subscription(telegram_id=YOUR_TELEGRAM_ID, days=30)
   ```

4. **Run Automation:**
   - Send `/autopilot` to run full automation
   - Check if it posts, engages, and connects

---

## 📊 Step 9: Monitor and Manage

### View Logs

```bash
# If running with nohup
tail -f bot.log

# If running with systemd
journalctl -u telegram-bot -f
```

### Database Management

The bot uses SQLite by default. Database location: `data/telegram_bot.db`

**View users:**
```bash
sqlite3 data/telegram_bot.db "SELECT * FROM users;"
```

**View subscriptions:**
```bash
sqlite3 data/telegram_bot.db "SELECT telegram_id, subscription_active, subscription_expires FROM users;"
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** — add it to `.gitignore`
2. **Use Stripe webhooks** for production to handle subscription updates
3. **Enable 2FA** on your Stripe account
4. **Rotate encryption keys** periodically
5. **Set up SSL** if you add webhook endpoints
6. **Monitor failed login attempts** to LinkedIn accounts

---

## 💰 Pricing Ideas

| Plan | Price | Features |
|------|-------|----------|
| Free Trial | $0 | 7 days, limited to 5 actions/day |
| Basic | $29/month | 50 actions/day, 1 LinkedIn account |
| Pro | $49/month | Unlimited actions, 3 accounts, priority support |
| Agency | $99/month | Unlimited everything, 10 accounts, white-label |

---

## 🚨 Important Legal Notes

⚠️ **LinkedIn ToS Compliance:**

Before launching this as a paid service, be aware:
- LinkedIn prohibits automation bots (Section 8.2 of User Agreement)
- Accounts using automation can be banned
- Selling automation tools creates legal exposure
- Consider pivoting to LinkedIn's official Marketing API for legitimate SaaS

**Safer alternatives:**
1. Use LinkedIn's official API (limited features but legal)
2. Sell as a "done-for-you" manual service
3. Teach it as an educational course
4. Keep it for personal use only

---

## 📞 Support

If users need help:
- Add `/help` command with troubleshooting
- Create a support channel: `@LinkedInGrowthSupport`
- Set up email support: support@yourdomain.com

---

## 🎉 You're Ready!

Your LinkedIn automation Telegram bot is now live!

Users can:
✅ Subscribe via Stripe
✅ Set up their LinkedIn profile
✅ Run automation via Telegram commands
✅ Track analytics
✅ Grow their network on autopilot

**Next steps:**
- Add more commands (schedule, custom posts, etc.)
- Build a landing page to promote your bot
- Set up email marketing for user retention
- Add referral system for viral growth

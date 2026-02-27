# 🚀 Quick Start Guide - LinkedInGrowthBot

Get your Telegram bot running in 10 minutes!

---

## 1️⃣ Get Bot Token (2 minutes)

1. Open Telegram, search `@BotFather`
2. Send `/newbot`
3. Name: `LinkedInGrowthBot`
4. Username: `LinkedInGrowthBot` (or any name ending in 'bot')
5. **Copy the token** you receive

---

## 2️⃣ Set Up Stripe (5 minutes)

1. Go to stripe.com and sign up
2. Dashboard → **Products** → **Add Product**
   - Name: `LinkedIn Bot Subscription`
   - Price: `$29/month` (recurring)
   - Save and **copy the Price ID**
3. Dashboard → **Developers** → **API Keys**
   - **Copy your Secret Key** (starts with `sk_test_`)

---

## 3️⃣ Configure Bot (2 minutes)

Create a `.env` file:

```bash
TELEGRAM_BOT_TOKEN=paste_your_bot_token_here
STRIPE_SECRET_KEY=paste_your_stripe_key_here
STRIPE_PRICE_ID=paste_your_price_id_here
ANTHROPIC_API_KEY=your_claude_api_key
ENCRYPTION_KEY=run_command_below_to_generate
```

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 4️⃣ Install & Run (1 minute)

```bash
# Install dependencies
pip install -r telegram_bot_requirements.txt

# Run the bot
python telegram_bot.py
```

---

## 🎉 You're Done!

Bot is live! Test with `/start` on Telegram.

---

## 📱 Mobile WebApp Quick Fix (Optional)

**Problem:** "📱 Post on Mobile" button doesn't work
**Solution (2 minutes):**

1. Download ngrok: https://ngrok.com/download
2. Run:
   ```bash
   # Terminal 1
   python webapp_server.py

   # Terminal 2
   ngrok http 8080
   ```
3. Copy ngrok URL (like `https://abc123.ngrok.io`)
4. Update `.env`: `WEBAPP_URL=https://abc123.ngrok.io`
5. Restart bot

---

## 🎮 Command Cheat Sheet

| What You Want | Command | Notes |
|---------------|---------|-------|
| **Start using bot** | `/start` | Use promo: **FREE** |
| **Generate post** | `/post` | AI-generated content |
| **Like posts** | `/engage` | Auto-engagement |
| **Full automation** | `/autopilot` | Post + Engage + Connect |
| **See stats** | `/stats` | Analytics dashboard |

---

## 🐛 Debugging

**Test all commands:**
```bash
python test_telegram_commands.py
```

**Common issues:**
- "Subscribe first" → Use promo code **FREE** in `/start`
- Mobile button fails → Run webapp server + ngrok
- AI errors → Check `ANTHROPIC_API_KEY` in .env

**Full docs:** See [TELEGRAM_BOT_DEBUG_SUMMARY.md](TELEGRAM_BOT_DEBUG_SUMMARY.md)

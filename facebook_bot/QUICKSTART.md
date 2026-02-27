# Facebook Bot - Quick Start Guide

## 5-Minute Setup

### 1. Get Facebook Credentials (5 min)

1. **Create Facebook App**: https://developers.facebook.com/apps/
   - Click "Create App" → "Business"
   - Name it anything (e.g., "Real Estate Bot")

2. **Add Messenger**:
   - Dashboard → "Add Product" → Find "Messenger" → "Set Up"

3. **Get Page Access Token**:
   - Messenger Settings → "Access Tokens"
   - Select your Facebook Page → "Generate Token"
   - **Copy this token** → This is `FACEBOOK_PAGE_ACCESS_TOKEN`

4. **Create Verify Token**:
   - Make up any random string (e.g., `my_bot_verify_123`)
   - **Save this** → This is `FACEBOOK_VERIFY_TOKEN`

5. **Get Page ID**:
   - Go to your Facebook Page
   - Click "About" → Find Page ID at bottom
   - **Copy this** → This is `FACEBOOK_PAGE_ID`

### 2. Update .env File

Open `.env` and fill in:

```env
FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxxxxxx  # From step 3
FACEBOOK_VERIFY_TOKEN=my_bot_verify_123   # From step 4
FACEBOOK_PAGE_ID=123456789                # From step 5

AGENT_NAME=John Tan                       # Your name
AGENT_PHONE=+65 9123 4567                 # Your phone

AGENT_TELEGRAM_ID=187767532               # Your Telegram ID (get from @userinfobot)
```

### 3. Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python facebook_bot/start_bot.py
```

You should see:
```
✅ BOT IS READY!
Webhook: http://0.0.0.0:8000/webhook
```

### 4. Expose to Internet (for testing)

Open new terminal:
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 5. Connect Webhook to Facebook

1. **Facebook App Dashboard** → Messenger → Webhooks
2. Click "Add Callback URL"
3. **Callback URL**: `https://abc123.ngrok.io/webhook`
4. **Verify Token**: `my_bot_verify_123` (same as .env)
5. **Subscribe to**:
   - ✅ messages
   - ✅ messaging_postbacks
   - ✅ feed
6. Click "Verify and Save"

If successful: ✅ Green checkmark!

### 6. Setup Page Features

```bash
python facebook_bot/setup_page.py
```

This configures:
- Get Started button
- Welcome greeting
- Persistent menu

### 7. Test It!

1. **Go to your Facebook Page**
2. **Click "Message"**
3. **You should see**: "Hi! I'm [Your Name]'s assistant..."
4. **Click "Get Started"**
5. **Bot should reply** with menu options!

---

## Testing Comment Auto-Reply

1. **Post on your Facebook Page** (any content)
2. **Comment**: "interested"
3. **Bot should**:
   - Reply to your comment: "Thanks! Check your messages"
   - Send you a DM automatically

---

## Testing Telegram Alerts

Update your lead to be "hot" (score 7+):

```python
from facebook_bot.db_handler import FacebookBotDB
db = FacebookBotDB()

# Create test hot lead alert
db.create_alert(
    lead_id=1,
    alert_type='hot_lead',
    alert_message='🔥 TEST: High-value lead from Facebook!'
)
```

**Check Telegram** → Should receive notification within 30 seconds!

---

## Common Issues

### "Webhook verification failed"
- ✅ Check `FACEBOOK_VERIFY_TOKEN` matches in .env and Facebook
- ✅ Ensure ngrok URL is HTTPS
- ✅ Bot must be running when you click "Verify"

### "Bot doesn't reply to comments"
- ✅ Webhook subscribed to "feed"? (Step 5)
- ✅ Comment contains trigger word? (try "interested", "price", "viewing")
- ✅ Check bot logs: `tail -f facebook_bot.log`

### "No Telegram alerts"
- ✅ `AGENT_TELEGRAM_ID` correct? (Message @userinfobot to get yours)
- ✅ `TELEGRAM_BOT_TOKEN` valid? (Get from @BotFather)
- ✅ Alert worker running? (Check startup logs)

---

## What Happens Next?

### When someone comments "interested":
1. ✅ Bot replies publicly: "Thanks! Check your DM"
2. ✅ Sends private DM with personalized message
3. ✅ Starts conversation flow
4. ✅ Qualifies lead (property type, budget, timeline)
5. ✅ Collects contact info (phone, email)
6. ✅ Calculates lead score 0-10
7. ✅ If score ≥ 7 → **Instant Telegram alert to you!**

### Hot Lead Alert Example:
```
🔥🔥 HOT LEAD ALERT! 🔥🔥

Name: Sarah Lim
Phone: +65 9123 4567
Score: 9/10

Details:
Intent: Buy
Budget: $1,800,000
Property: Condo
Location: Orchard
Timeline: Urgent (ASAP)

Messenger: m.me/123456789
```

---

## Production Deployment

For real usage (not testing):

1. **Deploy to cloud** (Heroku, Railway, DigitalOcean, etc.)
2. **Get permanent HTTPS domain**
3. **Update Facebook webhook** to production URL
4. **Use environment variables** (don't commit .env!)
5. **Monitor logs** and database

---

## Quick Commands

```bash
# Start bot
python facebook_bot/start_bot.py

# Setup page features
python facebook_bot/setup_page.py

# View current page settings
python facebook_bot/setup_page.py show

# Reset page settings
python facebook_bot/setup_page.py reset

# View bot stats
python -c "from facebook_bot.db_handler import FacebookBotDB; db = FacebookBotDB(); print(db.get_stats(7))"

# View hot leads
python -c "from facebook_bot.db_handler import FacebookBotDB; db = FacebookBotDB(); import json; print(json.dumps(db.get_hot_leads(), indent=2))"

# Test Telegram alerts
python facebook_bot/telegram_alerts.py
```

---

## Next Steps

1. ✅ Complete Facebook setup above
2. ✅ Test with a friend commenting on your post
3. ✅ Monitor first few conversations
4. 🔧 Customize messages in `templates.py`
5. 🔧 Adjust lead scoring in `config.py`
6. 🚀 Deploy to production
7. 📈 Scale and optimize!

---

## Support

- 📖 Full docs: [README.md](README.md)
- 🐛 Issues: Check `facebook_bot.log`
- 📊 Database: `SELECT * FROM fb_leads ORDER BY created_at DESC LIMIT 10;`

**You're all set!** 🚀

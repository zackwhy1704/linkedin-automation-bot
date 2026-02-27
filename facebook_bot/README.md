# Facebook Messenger Bot for Real Estate Lead Generation

Automated Facebook Messenger bot that:
- ✅ Auto-replies to comments on posts
- ✅ Qualifies leads through conversation flows
- ✅ Scores leads 0-10 based on intent, budget, timeline
- ✅ Sends hot lead alerts to agent's Telegram
- ✅ Manages follow-up sequences
- ✅ Tracks all conversations in PostgreSQL

---

## Quick Start

### 1. Facebook App Setup

1. **Create Facebook App**
   - Go to https://developers.facebook.com/apps/
   - Click "Create App" → Choose "Business" type
   - Name: "Your Name Real Estate Bot"

2. **Add Messenger Product**
   - In app dashboard, click "Add Product"
   - Find "Messenger" and click "Set Up"

3. **Connect Facebook Page**
   - Under Messenger Settings → Access Tokens
   - Select your Facebook Page
   - Click "Generate Token" → Copy the token
   - This is your `FACEBOOK_PAGE_ACCESS_TOKEN`

4. **Get Page ID**
   - Visit your Facebook Page
   - Click "About" → Find Page ID at bottom
   - This is your `FACEBOOK_PAGE_ID`

5. **Setup Webhooks**
   - Under Messenger Settings → Webhooks
   - Click "Add Callback URL"
   - Callback URL: `https://yourdomain.com/webhook`
   - Verify Token: Create a random string (e.g., `my_secure_verify_token_123`)
   - This is your `FACEBOOK_VERIFY_TOKEN`
   - Subscribe to fields:
     - ✅ messages
     - ✅ messaging_postbacks
     - ✅ feed

### 2. Environment Setup

Update your `.env` file:

```env
# Facebook Bot Configuration
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token_here
FACEBOOK_VERIFY_TOKEN=your_verify_token_here
FACEBOOK_PAGE_ID=your_page_id_here

# Agent Info
AGENT_NAME=Your Name
AGENT_PHONE=+65 8040 9026

# Telegram Alerts (use existing bot)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
AGENT_TELEGRAM_ID=your_telegram_chat_id
```

### 3. Database Migration

The schema has already been created. Verify tables exist:

```bash
python -c "from bot_database_postgres import BotDatabase; db = BotDatabase(); print(db.execute_query('SELECT COUNT(*) FROM fb_leads', fetch='one'))"
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies added:
- `facebook-sdk>=3.1.0` - Facebook Graph API client
- `uvicorn>=0.24.0` - ASGI server for FastAPI
- `requests>=2.31.0` - HTTP requests

### 5. Run the Bot

#### Option A: Run all components together (Recommended)

```bash
python facebook_bot/start_bot.py
```

This starts:
1. FastAPI webhook server (port 8000)
2. Telegram alert worker (background)

#### Option B: Run components separately

Terminal 1 - Webhook Server:
```bash
python facebook_bot/app.py
```

Terminal 2 - Telegram Alerts:
```bash
python facebook_bot/telegram_alerts.py
```

### 6. Expose Webhook to Internet

Facebook needs to reach your webhook. Use one of:

**ngrok** (for testing):
```bash
ngrok http 8000
```
Copy the HTTPS URL and use as callback URL in Facebook webhook settings.

**Production**: Deploy to cloud (Heroku, Railway, DigitalOcean, etc.)

### 7. Verify Webhook

After setting callback URL in Facebook, click "Verify and Save". If successful, you'll see a green checkmark.

### 8. Page Configuration

Set up Get Started button and Persistent Menu:

```python
from facebook_bot.setup_page import setup_facebook_page
setup_facebook_page()
```

---

## Features

### Auto-Reply to Comments

When someone comments on your post with trigger keywords:
- "interested", "price", "how much", "pm", "dm"
- "viewing", "see", "visit", "location"
- "valuation", "worth", "sell"

Bot will:
1. Reply publicly: "Thanks! I've sent you more details via DM"
2. Send private DM with personalized message
3. Start conversation flow

### Conversation Flows

**Property Search Flow**:
1. Ask property type (HDB/Condo/Landed)
2. Ask location preference
3. Ask budget range
4. Ask timeline
5. Collect contact info
6. Calculate lead score
7. Send to agent if hot lead (7+)

**Valuation Flow**:
1. Ask property address
2. Ask property type
3. Collect contact info
4. Create agent alert

**Appointment Flow**:
1. Ask preferred date/time
2. Collect contact info
3. Create agent alert

### Lead Scoring (0-10)

**Weighted Algorithm**:
- Intent (buy/sell/invest): +3 points
- Timeline urgent: +3 points
- Budget > $1.2M: +3 points
- Budget $600K-$1.2M: +2 points
- Phone provided: +2 points
- Email provided: +1 point

**Score 7+ = Hot Lead** → Instant Telegram alert to agent

### Telegram Agent Alerts

Hot leads (score 7+) trigger instant Telegram notification:

```
🔥🔥 HOT LEAD ALERT! 🔥🔥

Name: John Tan
Phone: +65 9123 4567
Score: 9/10

Details:
Intent: Buy
Budget: $1,500,000
Property: Condo
Location: Orchard
Timeline: Urgent (ASAP)

Facebook: fb.com/123456789
Messenger: m.me/123456789
```

### Follow-up Sequences

Hot leads automatically entered into follow-up sequences:
- +1 hour: Check-in message
- +24 hours: Property recommendations
- +3 days: Reminder to schedule viewing

---

## File Structure

```
facebook_bot/
├── __init__.py              # Package init
├── app.py                   # FastAPI webhook server ⭐
├── messenger_bot.py         # Main bot engine ⭐
├── comment_handler.py       # Auto-reply to comments ⭐
├── templates.py             # Message templates (buttons, quick replies)
├── db_handler.py            # Database operations
├── config.py                # Configuration
├── telegram_alerts.py       # Telegram notifications ⭐
├── start_bot.py            # Startup script
├── setup_page.py           # Page configuration helper
└── README.md               # This file
```

**⭐ Core files you'll interact with**

---

## Testing

### 1. Test Webhook Connection

```bash
curl http://localhost:8000/
# Should return: {"status":"Facebook Messenger Bot is running","version":"1.0"}
```

### 2. Test Comment Reply

1. Post on your Facebook Page
2. Comment with "interested"
3. Bot should:
   - Reply to comment
   - Send you a DM
   - Save lead in database

### 3. Test Conversation Flow

Send a message to your page:
1. "Hi" → Should show main menu
2. Click "Find Property"
3. Follow the conversation flow
4. At the end, check database:

```bash
python -c "from facebook_bot.db_handler import FacebookBotDB; db = FacebookBotDB(); print(db.get_hot_leads())"
```

### 4. Test Telegram Alerts

Update a lead to be "hot":

```python
from facebook_bot.db_handler import FacebookBotDB
db = FacebookBotDB()

# Create test alert
db.create_alert(
    lead_id=1,
    alert_type='hot_lead',
    alert_message='Test hot lead!'
)
```

Check your Telegram - should receive notification within 30 seconds.

---

## Configuration

### Trigger Keywords (config.py)

Edit `COMMENT_TRIGGERS` to customize:

```python
COMMENT_TRIGGERS = [
    'interested', 'price', 'how much',
    'viewing', 'pm', 'dm',
    'location', 'where', 'details',
    'valuation', 'sell', 'worth'
]
```

### Lead Scoring Weights (config.py)

Adjust `LEAD_SCORE_WEIGHTS`:

```python
LEAD_SCORE_WEIGHTS = {
    'intent_buy': 3,
    'timeline_urgent': 3,
    'budget_high': 3,
    'budget_mid': 2,
    'phone_provided': 2,
    'email_provided': 1,
}
```

### Budget Ranges (config.py)

Customize for your market:

```python
BUDGET_RANGES = {
    'low': (0, 600000),
    'mid': (600000, 1200000),
    'high': (1200000, 2000000),
    'luxury': (2000000, 999999999)
}
```

---

## Monitoring

### View Stats

```python
from facebook_bot.db_handler import FacebookBotDB
db = FacebookBotDB()

# Last 7 days
stats = db.get_stats(days=7)
print(f"Total Leads: {stats['total_leads']}")
print(f"Hot Leads: {stats['hot_leads']}")
print(f"Avg Score: {stats['avg_score']}/10")
```

### Check Pending Alerts

```python
db = FacebookBotDB()
alerts = db.get_pending_alerts()
print(f"{len(alerts)} pending alerts")
```

### View Conversation History

```python
db = FacebookBotDB()
history = db.get_conversation_history('facebook_user_id', limit=20)
for msg in history:
    print(f"{msg['direction']}: {msg['message_text']}")
```

---

## Troubleshooting

### Webhook verification fails
- Check `FACEBOOK_VERIFY_TOKEN` matches in .env and Facebook settings
- Ensure webhook URL is publicly accessible (use ngrok for testing)
- Check FastAPI logs for errors

### Bot doesn't reply to comments
- Verify webhook subscribed to "feed" field
- Check `COMMENT_TRIGGERS` includes the keyword used
- Check database: `SELECT * FROM fb_comment_replies ORDER BY replied_at DESC LIMIT 5;`

### No Telegram alerts
- Verify `TELEGRAM_BOT_TOKEN` and `AGENT_TELEGRAM_ID` in .env
- Check alert worker is running: `ps aux | grep telegram_alerts`
- Test manually: `python facebook_bot/telegram_alerts.py`

### Messages not sending
- Check `FACEBOOK_PAGE_ACCESS_TOKEN` is valid
- Token expires! Regenerate if bot stops working
- Check Facebook Page permissions (need "pages_messaging")

---

## Production Deployment

### Environment Variables

Set in production:
- `DATABASE_URL` - PostgreSQL connection string
- `FACEBOOK_PAGE_ACCESS_TOKEN` - Page access token
- `FACEBOOK_VERIFY_TOKEN` - Webhook verify token
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot
- `AGENT_TELEGRAM_ID` - Agent's Telegram chat ID

### Process Management

Use `supervisor` or `systemd` to keep bot running:

**supervisor config** (`/etc/supervisor/conf.d/facebook_bot.conf`):
```ini
[program:facebook_bot]
command=/path/to/venv/bin/python /path/to/facebook_bot/start_bot.py
directory=/path/to/linkedin-automation-bot
user=youruser
autostart=true
autorestart=true
stderr_logfile=/var/log/facebook_bot.err.log
stdout_logfile=/var/log/facebook_bot.out.log
```

### HTTPS Required

Facebook requires HTTPS for webhooks. Use:
- Nginx with Let's Encrypt SSL
- Cloud platform SSL (Heroku, Railway)
- Cloudflare proxy

---

## Next Steps

1. ✅ Complete Facebook app setup
2. ✅ Configure .env variables
3. ✅ Run bot and test webhook
4. ✅ Post on Facebook Page and test comment reply
5. ✅ Send test message and complete conversation flow
6. ✅ Verify Telegram alerts working
7. 🚀 Deploy to production
8. 📊 Monitor performance and optimize

---

## Support

Check logs for errors:
```bash
tail -f facebook_bot.log
```

Database issues:
```bash
python -c "from bot_database_postgres import BotDatabase; db = BotDatabase(); db.test_connection()"
```

Need help? Check the code comments in:
- `messenger_bot.py` - Main conversation logic
- `comment_handler.py` - Comment handling
- `app.py` - Webhook routing

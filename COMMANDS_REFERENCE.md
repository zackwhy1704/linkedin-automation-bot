# Telegram Bot Commands Reference

## ✅ SANITY TEST RESULTS - ALL PASSED!

**Bot Status:** @AI_LinkedIn_auto_bot (ID: 8517005273)
**All modules:** Working correctly ✅
**All handlers:** Registered ✅
**Database:** Connected ✅

---

## 📋 Available Commands

### 1. `/start` - Onboarding & Subscription
**Status:** ✅ Working
**Function:** `start()`
**Purpose:**
- New user onboarding
- Profile setup (industry, skills, goals, tone)
- LinkedIn credentials collection
- Content strategy configuration
- Subscription flow

**Flow:**
1. Industry → 2. Skills → 3. Goals → 4. Tone → 5. LinkedIn Email → 6. Password → 7. Content Themes → 8. Posting Times → 9. Content Goals → 10. Payment

**Stripe Integration:**
- Deep link handling for payment success/cancel
- Automatic subscription activation after payment
- Promo code support (e.g., FREETRIAL)

---

### 2. `/autopilot` - Full Automation
**Status:** ✅ Working
**Function:** `autopilot_command()`
**Background Worker:** `run_autopilot()`
**Purpose:** Run complete LinkedIn automation

**What it does:**
1. Generate and post AI content
2. Engage with feed (likes + comments)
3. Send connection requests

**Requirements:**
- Active subscription
- LinkedIn credentials set

---

### 3. `/engage` - Engagement Mode Selection
**Status:** ✅ Working (NEW OPTIONS!)
**Function:** `engage_command()`
**Callback Handler:** `handle_engage_callback()`

**Two Modes:**

#### Option 1: Reply to Comments (Recommended)
- **Worker:** `run_reply_engagement()`
- **Method:** `linkedin_bot.reply_based_engagement()`
- Only responds to people who commented on YOUR posts
- Builds genuine relationships
- Zero risk of duplicate comments

#### Option 2: Feed Engagement
- **Worker:** `run_engagement()`
- **Method:** `linkedin_bot.engage_with_feed()`
- Likes and comments on relevant posts in feed
- AI-filtered for relevance
- Now with triple duplicate protection

---

### 4. `/connect` - Send Connection Requests
**Status:** ✅ Working
**Function:** `connect_command()`
**Background Worker:** `run_connection_requests()`
**Purpose:** Search for and send personalized connection requests

**What it does:**
- Searches for relevant people
- Sends up to 5 connection requests
- Uses AI for personalization

---

### 5. `/schedule` - Schedule Content
**Status:** ✅ Working
**Function:** `schedule_command()`
**Callback Handler:** `handle_schedule_callback()`
**Purpose:** Schedule posts for specific times

**Features:**
- Uses your configured optimal posting times
- Shows time slots for selection
- Schedules AI-generated content

---

### 6. `/post` - Generate & Post Content
**Status:** ✅ Working (WITH VISIBLE BROWSER!)
**Function:** `post_command()`
**Callback Handler:** `handle_post_callback()`
**Background Worker:** `run_post_visible_browser()`

**Flow:**
1. Generates AI post based on your profile
2. Shows preview
3. Options: Approve, Regenerate, or Discard
4. **Opens visible browser (headless=False)**
5. Posts to LinkedIn in real-time

**You can watch the automation happen!**

---

### 7. `/stats` - View Analytics
**Status:** ✅ Working
**Function:** `stats_command()`
**Purpose:** Display your automation statistics

**Shows:**
- Posts created
- Likes given
- Comments made
- Connections sent
- Last active timestamp

---

### 8. `/settings` - Update Profile
**Status:** ✅ Working
**Function:** `settings_command()`
**Callback Handler:** `handle_settings_callback()`
**Message Handler:** `handle_settings_update()`

**Can update:**
- Industry
- Skills
- Career goals
- Tone preferences
- Content themes
- Posting times
- LinkedIn credentials

---

### 9. `/help` - Show Help Message
**Status:** ✅ Working
**Function:** `help_command()`
**Purpose:** Display all available commands

---

### 10. `/cancelsubscription` - Cancel Subscription
**Status:** ✅ Working
**Function:** `cancel_subscription_command()`
**Callback Handler:** `handle_cancel_subscription_callback()`

**Features:**
- Cancels Stripe subscription
- Sets `cancel_at_period_end=True`
- Keeps access until end of billing period
- Confirmation dialog before canceling

---

## 🔧 Background Worker Functions

All background functions verified working:

1. **`run_autopilot(telegram_id, bot)`**
   - Full automation cycle

2. **`run_engagement(telegram_id, bot)`**
   - Random feed engagement with AI filtering

3. **`run_reply_engagement(telegram_id, bot)`** ⭐ NEW
   - Reply-based engagement (safer!)

4. **`run_connection_requests(telegram_id, bot)`**
   - Automated networking

5. **`run_post_visible_browser(telegram_id, bot, generated_post)`** ⭐ NEW
   - Visible browser posting

---

## 🎯 Callback Handlers (All Registered)

1. **Subscription Management**
   - Pattern: `^(confirm_cancel_sub|keep_sub)$`
   - Handler: `handle_cancel_subscription_callback()`

2. **Settings Updates**
   - Pattern: `^(update_industry|update_skills|update_goals|update_tone|update_themes|update_times|update_credentials|cancel_settings)$`
   - Handler: `handle_settings_callback()`

3. **Post Management**
   - Pattern: `^(post_approve_|post_regenerate|post_discard)`
   - Handler: `handle_post_callback()`

4. **Schedule Management**
   - Pattern: `^(schedule_|schedule_cancel)`
   - Handler: `handle_schedule_callback()`

5. **Engagement Mode Selection** ⭐ NEW
   - Pattern: `^(engage_replies|engage_feed|engage_cancel)$`
   - Handler: `handle_engage_callback()`

---

## ✨ Recent Enhancements

### 1. Removed `/activate` Command
- Activation now automatic via Stripe callback
- Users redirected to `/start?payment_success` after payment
- Instant activation, no manual step needed

### 2. Fixed Duplicate Comment Bug
- Triple-layer protection:
  1. Database tracking (commented_posts.json)
  2. Visual verification (checks for existing comments)
  3. Stable post_id generation
- Now tracks all commented posts persistently

### 3. New Reply-Based Engagement
- Only responds to notifications about YOUR content
- Builds genuine relationships
- Zero random feed spam
- Recommended over random engagement

### 4. Visible Browser for `/post`
- Set `headless=False`
- Watch automation happen in real-time
- Great for debugging and verification

---

## 🗄️ Database & Data Files

### Database Tables (via BotDatabase):
- Users table
- Subscriptions tracking
- LinkedIn credentials (encrypted)
- User profiles
- Automation stats

### Data Files (All Present):
- `data/engagement_config.json` ✅
- `data/content_strategy.json` ✅
- `data/reply_templates.json` ✅
- `data/engaged_posts.json` (auto-created)
- `data/commented_posts.json` (auto-created)

---

## 🚀 How to Start the Bot

```bash
python telegram_bot.py
```

**Verification:**
```bash
# Run sanity tests
python test_bot_commands.py

# Test startup
python test_bot_startup.py
```

---

## 📱 Telegram Bot Info

- **Bot Username:** @AI_LinkedIn_auto_bot
- **Bot ID:** 8517005273
- **Bot Name:** LinkedInBot

---

## ⚠️ Important Notes

1. **Stripe Webhooks:** For production, set up Stripe webhooks for real-time subscription updates
2. **Encryption Key:** Keep `ENCRYPTION_KEY` secure - it encrypts LinkedIn passwords
3. **Rate Limits:** LinkedIn has rate limits - use reply-based engagement to stay safe
4. **Headless Mode:** Change `headless=True/False` in worker functions as needed

---

## 🆘 Troubleshooting

If commands aren't working:

1. **Check bot is running:**
   ```bash
   python telegram_bot.py
   ```

2. **Check environment variables:**
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Token:', 'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET')"
   ```

3. **Check subscription status:**
   - User must have active subscription for most commands
   - Use `/start` to subscribe

4. **Check LinkedIn credentials:**
   - Set via onboarding or `/settings`
   - Credentials are encrypted in database

5. **Run sanity test:**
   ```bash
   python test_bot_commands.py
   ```

---

**Last Tested:** 2026-02-16
**Status:** All systems operational ✅

# Mobile WebApp Setup Guide

## What This Does

Allows users to post to LinkedIn **from their mobile device** instead of from the server. When they use `/post`, they get two options:
- 📱 **Post on Mobile** - Opens LinkedIn in their Telegram browser (recommended, safe)
- 🖥️ **Post with Browser (Server)** - Uses Selenium on server (old method)

---

## Quick Setup (3 Steps)

### Step 1: Fix Network Connectivity

First, resolve the network error that's preventing the bot from connecting to Telegram:

```bash
# Run network diagnostic script
fix_network.bat
```

**If DNS is failing:**
1. Open Control Panel → Network and Internet → Network Connections
2. Right-click your network adapter → Properties
3. Select "Internet Protocol Version 4 (TCP/IPv4)" → Properties
4. Select "Use the following DNS server addresses"
5. Preferred DNS: `8.8.8.8` (Google DNS)
6. Alternate DNS: `8.8.4.4`
7. Click OK
8. Run `ipconfig /flushdns` in Command Prompt

**Then test:**
```bash
ping api.telegram.org
```

If successful, proceed to Step 2.

---

### Step 2: Install ngrok (for HTTPS)

Telegram WebApp **requires HTTPS**. Use ngrok to create a secure tunnel:

**Option A: Download and Install**
1. Go to https://ngrok.com/download
2. Download ngrok for Windows
3. Extract `ngrok.exe` to your project folder
4. Create free account at https://dashboard.ngrok.com
5. Copy your auth token
6. Run: `ngrok config add-authtoken YOUR_TOKEN`

**Option B: Using npm (if you have Node.js)**
```bash
npm install -g ngrok
```

---

### Step 3: Start Both Servers

**Terminal 1 - WebApp Server:**
```bash
python serve_webapp.py
```
Output:
```
Server running at: http://localhost:8080
WebApp URL: http://localhost:8080/linkedin_webapp.html
```

**Terminal 2 - ngrok Tunnel:**
```bash
ngrok http 8080
```
Output:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8080
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

**Update .env file:**
```bash
WEBAPP_URL=https://abc123.ngrok.io
```

**Terminal 3 - Telegram Bot:**
```bash
python telegram_bot.py
```

---

## Testing the Mobile WebApp

### 1. Send /post Command

In Telegram, send:
```
/post
```

### 2. You'll See Two Buttons

```
📱 Post on Mobile
🖥️ Post with Browser (Server)
```

### 3. Click "📱 Post on Mobile"

The WebApp will open in Telegram's in-app browser showing:
- Your generated post content
- Instructions on how to post
- "Copy Content" button
- "Open LinkedIn" button
- "I Posted It!" confirmation button

### 4. User Workflow

1. Click **"📋 Copy Content"** - copies post to clipboard
2. Click **"🔗 Open LinkedIn"** - opens LinkedIn in new tab
3. Click "Start a post" on LinkedIn
4. Paste the content (Ctrl+V or long-press → Paste)
5. Click "Post" on LinkedIn
6. Return to Telegram WebApp
7. Click **"✅ I Posted It!"**
8. WebApp closes automatically
9. Bot confirms and updates stats

---

## Troubleshooting

### Error: "WebApp won't open"

**Cause:** Not using HTTPS

**Solution:**
- Make sure you're using ngrok HTTPS URL in .env
- Don't use `http://localhost:8080` directly (won't work in Telegram)

### Error: "Cannot load WebApp"

**Cause:** ngrok tunnel expired or stopped

**Solution:**
```bash
# Restart ngrok
ngrok http 8080

# Copy new HTTPS URL (changes each time on free plan)
# Update .env with new URL
WEBAPP_URL=https://NEW_ID.ngrok.io

# Restart bot
python telegram_bot.py
```

### Error: "Post not confirmed"

**Cause:** WebApp couldn't send data back to bot

**Solution:**
- Check if bot is still running
- Check Telegram bot token is correct
- Try clicking "I Posted It!" again

---

## Production Deployment (Optional)

For permanent setup without ngrok:

### Option 1: GitHub Pages (Free)

1. Create new GitHub repository
2. Upload `linkedin_webapp.html`
3. Enable GitHub Pages in Settings
4. URL: `https://username.github.io/repo/linkedin_webapp.html`
5. Update .env: `WEBAPP_URL=https://username.github.io/repo`

### Option 2: Netlify/Vercel (Free)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod

# Copy URL (e.g., https://yourproject.vercel.app)
# Update .env
WEBAPP_URL=https://yourproject.vercel.app
```

### Option 3: AWS S3 + CloudFront

1. Create S3 bucket
2. Upload `linkedin_webapp.html`
3. Enable static website hosting
4. Create CloudFront distribution (for HTTPS)
5. URL: `https://abc123.cloudfront.net`
6. Update .env: `WEBAPP_URL=https://abc123.cloudfront.net`

---

## Comparison: Mobile vs Server Posting

| Feature | 📱 Mobile WebApp | 🖥️ Server Selenium |
|---------|-----------------|-------------------|
| **Where it runs** | User's phone | Server computer |
| **User sees it** | ✅ Yes | ❌ No |
| **LinkedIn safety** | ✅ Very safe | ⚠️ Risky (bot detection) |
| **Automation level** | Semi (70%) | Full (100%) |
| **Account suspension risk** | ✅ None | ⚠️ Possible |
| **Works on mobile** | ✅ Yes | ❌ No |
| **Setup complexity** | Medium (ngrok) | Easy |
| **User control** | ✅ Full | ❌ None |

**Recommendation:** Use 📱 Mobile WebApp for posting, keep 🖥️ Server Selenium for engagement (likes/comments only).

---

## How It Works Technically

```
┌─────────────┐
│   User      │
│  (Mobile)   │
└──────┬──────┘
       │ /post
       ▼
┌─────────────┐
│ Telegram    │
│    Bot      │──── Generates AI content
└──────┬──────┘
       │ Shows WebApp button
       ▼
┌─────────────┐
│  WebApp     │
│  (ngrok)    │──── Displays content + instructions
└──────┬──────┘
       │ User clicks "Open LinkedIn"
       ▼
┌─────────────┐
│  LinkedIn   │
│ (Browser)   │──── User manually posts
└──────┬──────┘
       │ Returns to WebApp
       ▼
┌─────────────┐
│  WebApp     │
│             │──── User clicks "I Posted It!"
└──────┬──────┘
       │ Sends confirmation
       ▼
┌─────────────┐
│ Telegram    │
│    Bot      │──── Updates stats, sends confirmation
└─────────────┘
```

---

## Security & Privacy

✅ **Safe because:**
- User is already logged into LinkedIn on their device
- No credentials shared with server
- No automation detection risk
- Full transparency (user sees everything)
- Complies with LinkedIn Terms of Service

⚠️ **Important:**
- ngrok free plan changes URL every restart
- Consider paid ngrok ($8/mo) for permanent URL
- Or use free hosting (GitHub Pages, Vercel)

---

## Next Steps

1. ✅ Fix network connectivity
2. ✅ Install ngrok
3. ✅ Start servers (webapp, ngrok, bot)
4. ✅ Test /post with mobile WebApp
5. 🔄 Deploy to permanent hosting (optional)
6. 🔄 AWS RDS migration (Week 2-4 of plan)

---

## Files Modified

- ✅ `telegram_bot.py` - Added WebApp button and data handler
- ✅ `linkedin_webapp.html` - WebApp interface (already created)
- ✅ `serve_webapp.py` - HTTP server for WebApp
- ✅ `.env` - Added WEBAPP_URL
- ✅ `MOBILE_BROWSER_SOLUTION.md` - Technical explanation
- ✅ `WEBAPP_SETUP_GUIDE.md` - This guide

---

## Support

If you encounter issues:
1. Check network connectivity first (`fix_network.bat`)
2. Verify ngrok is running and shows HTTPS URL
3. Check .env has correct WEBAPP_URL
4. Restart all three servers (webapp, ngrok, bot)
5. Test with /post command in Telegram

**Questions?** Review `MOBILE_BROWSER_SOLUTION.md` for technical details.

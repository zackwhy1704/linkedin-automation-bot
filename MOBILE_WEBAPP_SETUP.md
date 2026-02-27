# Mobile WebApp Setup Guide

## Problem
The Telegram bot's `/post` command shows a "📱 Post on Mobile" button, but it doesn't work because the WebApp isn't accessible from mobile devices.

## Root Cause
The `WEBAPP_URL` is set to `http://localhost:8080` which is only accessible from your local machine, not from mobile devices.

## Solution

### Option 1: Quick Local Testing with ngrok (Recommended for Development)

1. **Install ngrok** (if not already installed):
   ```bash
   # Download from https://ngrok.com/download
   # Or with chocolatey:
   choco install ngrok
   ```

2. **Start the WebApp server**:
   ```bash
   python webapp_server.py
   ```
   The server will run on `http://0.0.0.0:8080`

3. **In a new terminal, expose with ngrok**:
   ```bash
   ngrok http 8080
   ```

4. **Copy the ngrok URL** (looks like `https://abc123.ngrok.io`)

5. **Update your .env file**:
   ```env
   WEBAPP_URL=https://abc123.ngrok.io
   ```

6. **Restart the Telegram bot**:
   ```bash
   python telegram_bot.py
   ```

7. **Test on your phone**:
   - Open Telegram on your phone
   - Send `/post` command to your bot
   - Click "📱 Post on Mobile" button
   - The WebApp should now open!

### Option 2: Cloud Deployment (Production)

#### A. Deploy to Heroku

1. **Create `Procfile`**:
   ```
   web: python webapp_server.py
   ```

2. **Create `runtime.txt`**:
   ```
   python-3.11.0
   ```

3. **Deploy**:
   ```bash
   heroku create linkedin-bot-webapp
   heroku config:set WEBAPP_PORT=80
   git push heroku main
   ```

4. **Update .env**:
   ```env
   WEBAPP_URL=https://linkedin-bot-webapp.herokuapp.com
   ```

#### B. Deploy to Render

1. Go to https://render.com
2. Create new "Web Service"
3. Connect your GitHub repo
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python webapp_server.py`
5. Copy the deployed URL
6. Update .env with the URL

#### C. Deploy to Railway

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repo
4. Railway will auto-detect and deploy
5. Copy the generated URL
6. Update .env with the URL

## Verification

Run the test suite to verify everything works:

```bash
python test_telegram_commands.py
```

You should see:
```
✅ WebApp server accessible at https://your-url.com
```

## How the WebApp Works

1. User sends `/post` command
2. Bot generates content and shows preview
3. User clicks "📱 Post on Mobile" button
4. Telegram opens the WebApp in an in-app browser
5. User sees the post content and can:
   - Copy the content
   - Open LinkedIn
   - Paste and post manually
   - Click "I Posted It!" to confirm

## Troubleshooting

### WebApp button doesn't respond
- **Cause**: WEBAPP_URL is not publicly accessible
- **Solution**: Use ngrok or deploy to cloud

### WebApp shows "Loading post content..."
- **Cause**: Content not passed in URL
- **Check**: URL should have `?content=...&user_id=...&post_id=...`

### "Copy Content" button doesn't work
- **Cause**: Clipboard API requires HTTPS
- **Solution**: Use ngrok (provides HTTPS) or deploy with SSL

### WebApp closes immediately
- **Cause**: JavaScript error
- **Check**: Browser console for errors
- **Test**: Open `/test` endpoint: `https://your-url.com/test`

## Testing Commands

### Test all commands:
```bash
python test_telegram_commands.py
```

### Test WebApp server only:
```bash
curl http://localhost:8080/health
# Should return: {"status":"healthy","service":"linkedin-bot-webapp"}
```

### Test WebApp loading:
```bash
curl http://localhost:8080/linkedin_webapp.html
# Should return HTML content
```

## Environment Variables Reference

Add to `.env` file:

```env
# WebApp Server Configuration
WEBAPP_URL=https://your-ngrok-or-cloud-url.com
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8080
```

## Architecture

```
User's Phone (Telegram App)
        ↓
Telegram Servers
        ↓
Your Bot Server (telegram_bot.py)
        ↓ [Returns WebApp URL]
        ↓
User's Phone opens WebApp
        ↓
WebApp Server (webapp_server.py)
        ↓ [Serves linkedin_webapp.html]
        ↓
User sees content, copies, posts to LinkedIn
        ↓
User clicks "I Posted It!"
        ↓
WebApp sends data back to bot
```

## Quick Start (All-in-One)

```bash
# 1. Start WebApp server (Terminal 1)
python webapp_server.py

# 2. Start ngrok (Terminal 2)
ngrok http 8080

# 3. Copy ngrok URL and update .env
# WEBAPP_URL=https://abc123.ngrok.io

# 4. Start Telegram bot (Terminal 3)
python telegram_bot.py

# 5. Test on phone
# Send /post to your bot
# Click "📱 Post on Mobile"
# Should open WebApp!
```

## Notes

- ngrok URLs change every time you restart (free tier)
- For production, use a permanent cloud deployment
- WebApp server is lightweight (FastAPI) - very fast
- The HTML file is static - no database needed
- All Telegram WebApps must use HTTPS (ngrok provides this)

# Auto-Close Webview After Payment - Setup Guide

## Problem
After successful Stripe payment, the webview stays open and users have to manually close it.

## Solution
Created dedicated success/cancel pages that automatically close the Telegram webview using the Telegram WebApp API.

---

## Files Created

### 1. HTML Pages (Auto-Close)
- **[static/payment_success.html](static/payment_success.html)** - Success page with auto-close (2 seconds)
- **[static/payment_cancel.html](static/payment_cancel.html)** - Cancel page with auto-close (2 seconds)

### 2. Payment Server
- **[payment_server.py](payment_server.py)** - Flask server to serve the HTML pages
- **[start_payment_server.bat](start_payment_server.bat)** - Quick start script

### 3. Updated Code
- **[telegram_bot.py](telegram_bot.py)** - Updated Stripe URLs to use payment server
- **[requirements.txt](requirements.txt)** - Added Flask dependency

---

## How It Works

1. **User clicks payment button** → Opens Stripe checkout in webview
2. **Payment completes** → Stripe redirects to `PAYMENT_SERVER_URL/payment/success`
3. **Success page loads** → Shows checkmark animation + "Closing in 2..."
4. **Auto-close triggers** → Uses multiple methods:
   - `Telegram.WebApp.close()` (primary)
   - `window.close()` (fallback)
   - `TelegramWebviewProxy.postEvent('web_app_close')` (Telegram-specific)
   - Redirect to bot as last resort
5. **Webview closes** → User returns to Telegram bot

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install Flask
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

Add to `.env` file (already added):
```bash
# Payment Server URL
# For local testing: use ngrok URL
# For production: use your domain
PAYMENT_SERVER_URL=http://localhost:5000
```

### Step 3: Local Testing (Development)

#### Option A: Localhost (Limited - Stripe won't redirect properly)

1. **Start payment server:**
   ```bash
   python payment_server.py
   ```
   Or double-click: `start_payment_server.bat`

2. **Start Telegram bot:**
   ```bash
   python telegram_bot.py
   ```

**Limitation:** Stripe can't redirect to `localhost` from their servers. Use ngrok instead.

#### Option B: Ngrok (Recommended for Testing)

1. **Install ngrok:**
   - Download from https://ngrok.com/download
   - Extract to any folder
   - Sign up and get auth token

2. **Start payment server:**
   ```bash
   python payment_server.py
   ```

3. **Start ngrok tunnel (in new terminal):**
   ```bash
   ngrok http 5000
   ```

   You'll see:
   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:5000
   ```

4. **Update `.env` with ngrok URL:**
   ```bash
   PAYMENT_SERVER_URL=https://abc123.ngrok.io
   ```

5. **Restart Telegram bot:**
   ```bash
   python telegram_bot.py
   ```

6. **Test payment:**
   - Go through onboarding
   - Click payment button
   - Complete Stripe checkout
   - Webview should auto-close after 2 seconds ✅

---

## Production Deployment

### Option 1: Deploy Payment Server with Bot (Same Server)

Update `.env` on production server:
```bash
# Use your domain
PAYMENT_SERVER_URL=https://yourdomain.com
```

Add payment server to systemd service:
```bash
# Start both services
sudo systemctl start linkedin-bot
sudo systemctl start linkedin-payment-server
```

### Option 2: Separate Payment Server (Recommended)

Deploy payment server separately (e.g., Vercel, Netlify, AWS S3 + CloudFront):

**Vercel Deployment:**
1. Create `vercel.json`:
   ```json
   {
     "rewrites": [
       { "source": "/payment/success", "destination": "/static/payment_success.html" },
       { "source": "/payment/cancel", "destination": "/static/payment_cancel.html" }
     ]
   }
   ```

2. Deploy:
   ```bash
   vercel --prod
   ```

3. Update `.env`:
   ```bash
   PAYMENT_SERVER_URL=https://your-project.vercel.app
   ```

---

## Testing Checklist

### Test Success Flow
- [ ] Go through bot onboarding
- [ ] Click "Subscribe" button
- [ ] Stripe checkout opens in webview
- [ ] Enter test card: `4242 4242 4242 4242`
- [ ] Complete payment
- [ ] Success page shows with checkmark ✓
- [ ] Countdown shows "Closing in 2..."
- [ ] Webview automatically closes after 2 seconds
- [ ] Back in Telegram bot
- [ ] Subscription activated

### Test Cancel Flow
- [ ] Start payment process
- [ ] Click "Cancel" in Stripe checkout
- [ ] Cancel page shows with X mark
- [ ] Countdown shows "Closing in 2..."
- [ ] Webview automatically closes
- [ ] Back in Telegram bot

---

## Troubleshooting

### Issue: Webview doesn't close

**Causes:**
1. Telegram WebApp API not loaded
2. JavaScript blocked
3. Wrong Telegram bot username in URL

**Solutions:**
1. Check browser console for errors
2. Verify Telegram WebApp script loads: `https://telegram.org/js/telegram-web-app.js`
3. Ensure bot username is correct in URL parameters

### Issue: Stripe doesn't redirect

**Causes:**
1. PAYMENT_SERVER_URL is `localhost` (not accessible from Stripe servers)
2. Payment server not running
3. Ngrok tunnel expired

**Solutions:**
1. Use ngrok for local testing
2. Verify payment server is running: `http://localhost:5000/health`
3. Restart ngrok and update URL in `.env`

### Issue: "Connection refused"

**Cause:** Payment server not running

**Solution:**
```bash
# Check if running
curl http://localhost:5000/health

# Start server
python payment_server.py
```

---

## Advanced Customization

### Change Auto-Close Delay

Edit `static/payment_success.html` line 123:
```javascript
setTimeout(function() {
    // ...close webview
}, 2000);  // Change 2000 to desired milliseconds (e.g., 3000 = 3 seconds)
```

### Customize Success Page

Edit `static/payment_success.html`:
- Change colors in `<style>` section
- Modify text in `<h1>` and `<p>` tags
- Add your branding/logo

### Add Analytics

Add tracking to success page:
```javascript
// Google Analytics
gtag('event', 'purchase', {
    transaction_id: '{{transaction_id}}',
    value: 0.99,
    currency: 'USD'
});
```

---

## URLs Overview

| Environment | Payment Server URL | Example |
|-------------|-------------------|---------|
| **Local (Limited)** | http://localhost:5000 | Won't work with Stripe |
| **Development (Ngrok)** | https://abc123.ngrok.io | ✅ Works for testing |
| **Staging** | https://staging.yourdomain.com | ✅ Production-ready |
| **Production** | https://yourdomain.com | ✅ Production |

---

## Security Notes

1. **HTTPS Required:** Stripe requires HTTPS for redirect URLs in production
2. **CORS:** Not needed since pages are served directly (not API calls)
3. **Bot Username Validation:** Pages verify bot username in URL params
4. **No Sensitive Data:** Success/cancel pages don't handle payment data

---

## Monitoring

### Check Payment Server Health

```bash
curl http://localhost:5000/health
# Should return: {"status": "ok"}
```

### Check Success Page

```bash
curl http://localhost:5000/payment/success?bot=your_bot_name
# Should return HTML with Telegram WebApp script
```

### Logs

Payment server logs all requests to console:
```
127.0.0.1 - - [16/Feb/2026 12:00:00] "GET /payment/success?bot=LinkedInBot HTTP/1.1" 200 -
```

---

## Summary

✅ **Created:** Auto-closing success/cancel pages
✅ **Updated:** Stripe redirect URLs
✅ **Added:** Flask payment server
✅ **Configured:** Environment variables

**Status:** Ready to test!

**Next Steps:**
1. Start payment server
2. Start ngrok (for local testing)
3. Update PAYMENT_SERVER_URL in `.env`
4. Test payment flow end-to-end

The webview will now automatically close 2 seconds after successful payment! 🎉

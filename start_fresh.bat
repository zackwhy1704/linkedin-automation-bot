@echo off
echo ========================================
echo CLEAN START - Mobile Posting Test
echo ========================================
echo.

echo Step 1: Stopping all Python processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 3 >nul

echo Step 2: Waiting for Telegram conflict to clear (30 seconds)...
echo          (Telegram needs time to recognize old bot disconnected)
timeout /t 30 >nul

echo Step 3: Starting WebApp server...
start "WebApp Server" cmd /k "python serve_webapp.py"
timeout /t 2 >nul

echo Step 4: Starting HTTPS tunnel (localtunnel)...
start "HTTPS Tunnel" cmd /k "lt --port 8080"
timeout /t 3 >nul

echo.
echo ========================================
echo Ready to start bot!
echo ========================================
echo.
echo IMPORTANT:
echo 1. Check the "HTTPS Tunnel" window for the URL
echo 2. If URL changed, update .env:
echo    WEBAPP_URL=https://new-url.loca.lt
echo.
echo 3. Then start the bot:
echo    python telegram_bot.py
echo.
echo 4. In Telegram, send: /post
echo.
pause

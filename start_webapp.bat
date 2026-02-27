@echo off
echo.
echo ========================================
echo LinkedIn Bot - WebApp Server Launcher
echo ========================================
echo.
echo Starting WebApp server on port 8080...
echo.
echo For mobile access, you need to expose this with ngrok:
echo   1. Install ngrok: https://ngrok.com/download
echo   2. Run: ngrok http 8080
echo   3. Copy the ngrok URL (https://xxxxx.ngrok.io)
echo   4. Update WEBAPP_URL in .env file
echo   5. Restart the telegram bot
echo.
echo ========================================
echo.

python webapp_server.py

pause

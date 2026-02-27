@echo off
echo ========================================
echo Checking for Running Bot Instances
echo ========================================
echo.

echo Python processes currently running:
tasklist | findstr python.exe
echo.

echo ========================================
echo Checking if port 8080 is in use:
netstat -ano | findstr :8080
echo.

echo ========================================
echo Checking Telegram bot connection:
curl -s "https://api.telegram.org/bot8517005273:AAGk7pnzmTylCkFdBJdzHhZtloo2B8bNsZ4/getMe"
echo.
echo.

echo ========================================
echo If you see multiple python.exe processes,
echo run start_fresh.bat to kill them all
echo and start clean.
echo ========================================
pause

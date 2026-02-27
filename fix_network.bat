@echo off
echo ========================================
echo Network Diagnostics for Telegram Bot
echo ========================================
echo.

echo 1. Testing internet connectivity...
ping -n 3 8.8.8.8
echo.

echo 2. Testing DNS resolution...
nslookup api.telegram.org
echo.

echo 3. Testing Telegram API connectivity...
ping -n 3 api.telegram.org
echo.

echo 4. Flushing DNS cache...
ipconfig /flushdns
echo.

echo 5. Testing connection again...
nslookup api.telegram.org
echo.

echo ========================================
echo If DNS still fails, try:
echo 1. Change DNS to Google DNS (8.8.8.8)
echo 2. Disable VPN/Proxy if active
echo 3. Check Windows Firewall settings
echo 4. Restart your router
echo ========================================
pause

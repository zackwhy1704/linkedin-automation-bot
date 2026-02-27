@echo off
echo ========================================
echo Cloudflare Tunnel Setup (No Password!)
echo ========================================
echo.

echo Downloading Cloudflare Tunnel...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"

echo.
echo Starting tunnel on port 8080...
echo.
echo Press Ctrl+C to stop
echo.

cloudflared.exe tunnel --url http://localhost:8080

pause

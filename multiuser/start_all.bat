@echo off
REM Multi-User LinkedIn Bot - Start All Services
REM Starts: Redis, Celery, WebApp Server, Cloudflare Tunnel, Telegram Bot

echo.
echo ========================================
echo Multi-User LinkedIn Bot Launcher
echo ========================================
echo.
echo This will start 5 services:
echo 1. Redis/Memurai  (Task Queue)
echo 2. Celery Worker  (Background Tasks)
echo 3. WebApp Server  (Mobile Posting)
echo 4. Cloudflare Tunnel (Public HTTPS URL)
echo 5. Telegram Bot   (User Interface)
echo.
pause

REM -------------------------------------------------------
REM 1. Redis / Memurai
REM -------------------------------------------------------
echo [1/5] Checking Redis/Memurai...
netstat -an | findstr ":6379" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [SKIP] Redis already running on port 6379
) else (
    where memurai.exe >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [START] Starting Memurai...
        start "Memurai Server" memurai.exe
    ) else (
        where redis-server >nul 2>nul
        if %ERRORLEVEL% EQU 0 (
            echo [START] Starting redis-server...
            start "Redis Server" redis-server
        ) else (
            echo [ERROR] Redis/Memurai not found! Install Memurai from https://www.memurai.com
            pause
            exit /b 1
        )
    )
    timeout /t 3 /nobreak >nul
)

REM -------------------------------------------------------
REM 2. Celery Worker
REM -------------------------------------------------------
echo [2/5] Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0.. && python -m celery -A celery_app worker --loglevel=info --concurrency=3 --pool=solo"
timeout /t 5 /nobreak >nul

REM -------------------------------------------------------
REM 3. WebApp Server (port 8080)
REM -------------------------------------------------------
echo [3/5] Starting WebApp Server on port 8080...
start "WebApp Server" cmd /k "cd /d %~dp0.. && python webapp_server.py"
timeout /t 3 /nobreak >nul

REM -------------------------------------------------------
REM 4. Cloudflare Tunnel
REM -------------------------------------------------------
echo [4/5] Starting Cloudflare Tunnel...
if exist "%~dp0..\cloudflared.exe" (
    start "Cloudflare Tunnel" cmd /k "cd /d %~dp0.. && cloudflared.exe tunnel --url http://localhost:8080"
    echo [INFO] Cloudflare tunnel starting - check that window for the HTTPS URL
    echo [INFO] Copy the URL and update WEBAPP_URL in .env if it changed
    timeout /t 8 /nobreak >nul
) else (
    echo [WARN] cloudflared.exe not found - skipping tunnel
    echo [INFO] Mobile posting will only work on local network
)

REM -------------------------------------------------------
REM 5. Telegram Bot
REM -------------------------------------------------------
echo [5/5] Starting Telegram Bot (Multi-User Mode)...
start "Telegram Bot" cmd /k "cd /d %~dp0 && python telegram_bot_multiuser.py"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Windows open:
echo   - Celery Worker
echo   - WebApp Server
echo   - Cloudflare Tunnel  ^<-- Copy the https://... URL to .env WEBAPP_URL
echo   - Telegram Bot
echo.
echo IMPORTANT: If the Cloudflare URL changed, update .env:
echo   WEBAPP_URL=https://your-new-url.trycloudflare.com
echo   Then restart the Telegram Bot window.
echo.
echo To stop all: close each window, or run stop_all.bat
echo.
pause

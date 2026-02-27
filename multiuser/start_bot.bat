@echo off
REM Start Multi-User Telegram Bot

cd /d %~dp0

echo.
echo ========================================
echo LinkedIn Telegram Bot - Multi-User Mode
echo ========================================
echo.
echo This bot supports MULTIPLE CONCURRENT USERS!
echo.
echo Requirements:
echo   1. Redis Server must be running
echo   2. Celery Worker must be running
echo   3. PostgreSQL database must be accessible
echo.
echo If Redis/Celery are not running, the bot will
echo fall back to single-user threading mode.
echo.
echo ========================================
echo.

python telegram_bot_multiuser.py

pause

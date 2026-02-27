@echo off
REM Start Celery Worker for LinkedIn Bot

cd /d %~dp0..

echo.
echo ========================================
echo Celery Worker for LinkedIn Bot
echo ========================================
echo.
echo This worker processes LinkedIn automation tasks
echo in the background for multiple users concurrently.
echo.
echo Configuration:
echo   - Concurrency: 3 parallel tasks
echo   - Pool: Solo (Windows compatibility)
echo   - Queues: posting, engagement, connections
echo.
echo Keep this window open while the bot is running.
echo Press Ctrl+C to stop the worker.
echo.
echo ========================================
echo.

celery -A celery_app worker --loglevel=info --concurrency=3 --pool=solo

pause

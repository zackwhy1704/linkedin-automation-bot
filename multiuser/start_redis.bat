@echo off
REM Start Redis Server for LinkedIn Bot

echo Starting Redis Server on port 6379...
echo.
echo This is the task queue backend for multi-user support.
echo Keep this window open while the bot is running.
echo.
echo Press Ctrl+C to stop Redis
echo.

redis-server

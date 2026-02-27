@echo off
REM Manual WSL Redis Installation
echo.
echo Installing Redis via WSL...
echo.
echo Running: wsl sudo apt update
wsl sudo apt update

echo.
echo Running: wsl sudo apt install -y redis-server
wsl sudo apt install -y redis-server

echo.
echo Starting Redis...
wsl sudo service redis-server start

echo.
echo Testing Redis...
wsl redis-cli ping

echo.
echo If you see "PONG", Redis is working!
echo.
pause

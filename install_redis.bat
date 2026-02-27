@echo off
REM Redis Installation Script for Windows
REM This script downloads and sets up Redis without admin rights

echo.
echo ========================================
echo Redis Installation for Windows
echo ========================================
echo.

REM Check if Redis is already installed
where redis-server >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis is already installed!
    redis-server --version
    goto :test
)

echo [INFO] Redis not found. Installing...
echo.

REM Option 1: Try WSL (if available)
where wsl >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] WSL detected. Installing Redis via WSL...
    echo.

    wsl sudo apt update
    wsl sudo apt install -y redis-server

    echo.
    echo [OK] Redis installed via WSL!
    echo.
    echo To start Redis, run:
    echo   wsl redis-server
    echo.
    goto :test
)

REM Option 2: Download portable version
echo [INFO] Downloading Redis portable version...
echo.

REM Create Redis directory
if not exist "C:\Users\%USERNAME%\Redis" mkdir "C:\Users\%USERNAME%\Redis"
cd /d "C:\Users\%USERNAME%\Redis"

REM Download Redis for Windows (Memurai Developer Edition - free Redis alternative)
echo Downloading Memurai Developer Edition (Redis for Windows)...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.memurai.com/get-memurai' -OutFile 'memurai.msi'}"

if exist memurai.msi (
    echo.
    echo [OK] Download complete!
    echo.
    echo MANUAL INSTALLATION REQUIRED:
    echo 1. Open File Explorer
    echo 2. Navigate to: C:\Users\%USERNAME%\Redis
    echo 3. Double-click memurai.msi
    echo 4. Follow the installation wizard
    echo 5. After installation, restart this script
    echo.
    start explorer "C:\Users\%USERNAME%\Redis"
    pause
    goto :test
) else (
    echo.
    echo [ERROR] Download failed!
    echo.
    echo MANUAL INSTALLATION OPTIONS:
    echo.
    echo === Option A: Memurai (Recommended) ===
    echo 1. Visit: https://www.memurai.com/get-memurai
    echo 2. Download Memurai Developer Edition (FREE)
    echo 3. Install with default settings
    echo 4. Restart this script
    echo.
    echo === Option B: Docker ===
    echo If you have Docker installed:
    echo   docker run -d -p 6379:6379 --name redis redis
    echo.
    echo === Option C: WSL ===
    echo 1. Install WSL: wsl --install
    echo 2. Restart computer
    echo 3. Run: wsl sudo apt install redis-server
    echo 4. Start: wsl redis-server
    echo.
    pause
    exit /b 1
)

:test
echo.
echo ========================================
echo Testing Redis Installation
echo ========================================
echo.

REM Try to start Redis in background
start "Redis Server" /MIN redis-server

REM Wait for Redis to start
timeout /t 3 /nobreak >nul

REM Test connection
echo Testing Redis connection...
redis-cli ping >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis is running and responding!
    echo.
    goto :success
) else (
    REM Try WSL
    wsl redis-cli ping >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Redis is running in WSL!
        echo.
        echo To use Redis, always start it with:
        echo   wsl redis-server
        echo.
        goto :success
    ) else (
        echo [WARNING] Redis installed but not responding
        echo.
        echo Try starting it manually:
        echo   redis-server
        echo.
        echo Or with WSL:
        echo   wsl redis-server
        echo.
        goto :end
    )
)

:success
echo ========================================
echo Installation Successful!
echo ========================================
echo.
echo Redis is now ready for use!
echo.
echo Next steps:
echo 1. Keep Redis running (don't close the Redis window)
echo 2. Run the multi-user bot:
echo    cd multiuser
echo    start_all.bat
echo.
echo ========================================

:end
pause

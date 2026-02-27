@echo off
REM =============================================================================
REM LinkedIn Bot - Export Local PostgreSQL Database (Windows)
REM Run this on your Windows machine BEFORE migrating to the server
REM =============================================================================

echo.
echo ============================================
echo LinkedIn Bot - Export Local Database
echo ============================================
echo.

REM Set these to match your local .env settings
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=linkedin_bot
set DB_USER=postgres

set EXPORT_FILE=linkedin_bot_export.sql

echo Exporting database '%DB_NAME%' to %EXPORT_FILE% ...
echo (You will be prompted for your PostgreSQL password)
echo.

pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% --no-owner --no-acl -f %EXPORT_FILE%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Export successful: %EXPORT_FILE%
    echo.
    echo NEXT: Upload to your server:
    echo   scp %EXPORT_FILE% root@YOUR_SERVER_IP:/home/linkedin/linkedin-automation-bot/
    echo.
    echo Then on the server, run:
    echo   bash deployment/migrate_db_import.sh
) else (
    echo.
    echo [ERROR] pg_dump failed. Make sure:
    echo   - PostgreSQL is running
    echo   - pg_dump is in your PATH (usually C:\Program Files\PostgreSQL\15\bin)
    echo   - Database name and credentials are correct
)

pause

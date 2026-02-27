@echo off
REM PostgreSQL Setup Script for Windows
REM Run this as Administrator

echo ============================================================
echo POSTGRESQL SETUP FOR WINDOWS
echo ============================================================
echo.

REM Check if PostgreSQL is installed
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PostgreSQL not found in PATH
    echo.
    echo Please add PostgreSQL to your PATH:
    echo 1. Find your PostgreSQL installation folder (usually C:\Program Files\PostgreSQL\15\bin)
    echo 2. Add it to System PATH environment variable
    echo 3. Restart this terminal
    echo.
    pause
    exit /b 1
)

echo [OK] PostgreSQL found in PATH
echo.

REM Step 1: Check PostgreSQL service status
echo Step 1: Checking PostgreSQL service...
sc query "postgresql-x64-15" | find "RUNNING" >nul
if %errorlevel% equ 0 (
    echo [OK] PostgreSQL service is running
) else (
    echo [WARNING] PostgreSQL service is not running
    echo Starting PostgreSQL service...
    net start postgresql-x64-15
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to start PostgreSQL. Try running as Administrator.
        pause
        exit /b 1
    )
    echo [OK] PostgreSQL service started
)
echo.

REM Step 2: Test connection
echo Step 2: Testing PostgreSQL connection...
echo Please enter your PostgreSQL password when prompted.
echo (Default user: postgres)
echo.

psql -U postgres -c "SELECT version();" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo PASSWORD HELP
    echo ============================================================
    echo.
    echo If you forgot your PostgreSQL password, you can reset it:
    echo.
    echo Option 1: Use pgAdmin (GUI)
    echo   1. Open pgAdmin
    echo   2. Right-click "postgres" user
    echo   3. Select "Properties" ^> "Definition"
    echo   4. Enter new password
    echo.
    echo Option 2: Command line (requires admin)
    echo   1. Stop PostgreSQL service
    echo   2. Edit pg_hba.conf (change md5 to trust)
    echo   3. Restart service
    echo   4. Run: psql -U postgres
    echo   5. Run: ALTER USER postgres PASSWORD 'newpassword';
    echo   6. Revert pg_hba.conf changes
    echo.
    echo After resetting, run this script again.
    echo ============================================================
    pause
    exit /b 1
)

echo [OK] Successfully connected to PostgreSQL
echo.

REM Step 3: Create database
echo Step 3: Creating database 'linkedin_bot'...
psql -U postgres -c "CREATE DATABASE linkedin_bot;" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Database 'linkedin_bot' created successfully
) else (
    echo [INFO] Database might already exist. Checking...
    psql -U postgres -c "\l" | find "linkedin_bot" >nul
    if %errorlevel% equ 0 (
        echo [OK] Database 'linkedin_bot' already exists
    ) else (
        echo [ERROR] Failed to create database
        pause
        exit /b 1
    )
)
echo.

REM Step 4: Test database connection
echo Step 4: Testing database connection...
psql -U postgres -d linkedin_bot -c "SELECT current_database();" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Cannot connect to linkedin_bot database
    pause
    exit /b 1
)
echo [OK] Successfully connected to linkedin_bot database
echo.

REM Step 5: Show next steps
echo ============================================================
echo SUCCESS! PostgreSQL is ready.
echo ============================================================
echo.
echo Database created: linkedin_bot
echo Database user: postgres
echo.
echo NEXT STEPS:
echo.
echo 1. Update your .env file with PostgreSQL credentials:
echo    DATABASE_HOST=localhost
echo    DATABASE_PORT=5432
echo    DATABASE_NAME=linkedin_bot
echo    DATABASE_USER=postgres
echo    DATABASE_PASSWORD=your_password_here
echo.
echo 2. Run schema creation:
echo    psql -U postgres -d linkedin_bot -f migrations\schema.sql
echo.
echo 3. Test connection:
echo    python test_postgres_connection.py
echo.
echo 4. Migrate data:
echo    python migrations\migrate_sqlite_to_postgres.py
echo.
echo ============================================================
pause

"""
Interactive PostgreSQL Database Setup
Helps create the database and test connection
"""

import subprocess
import sys
import os
import getpass

# PostgreSQL paths
PSQL_PATH = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
CREATEDB_PATH = r"C:\Program Files\PostgreSQL\18\bin\createdb.exe"

print("=" * 60)
print("POSTGRESQL DATABASE SETUP")
print("=" * 60)
print()

# Verify PostgreSQL is installed
if not os.path.exists(PSQL_PATH):
    print(f"[ERROR] PostgreSQL not found at: {PSQL_PATH}")
    print()
    print("Please check your PostgreSQL installation path.")
    sys.exit(1)

print("[OK] Found PostgreSQL 18")
print()

# Get password
print("Enter your PostgreSQL password")
print("(This is the password you set during PostgreSQL installation)")
password = getpass.getpass("Password for user 'postgres': ")

if not password:
    print("[ERROR] Password is required!")
    sys.exit(1)

print()
print("=" * 60)
print("STEP 1: Testing PostgreSQL Connection")
print("=" * 60)
print()

# Test connection
try:
    env = os.environ.copy()
    env['PGPASSWORD'] = password

    result = subprocess.run(
        [PSQL_PATH, '-U', 'postgres', '-c', 'SELECT version();'],
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        print("[OK] Successfully connected to PostgreSQL!")
        # Extract version
        for line in result.stdout.split('\n'):
            if 'PostgreSQL' in line:
                print(f"[OK] Version: {line.strip()}")
                break
    else:
        print("[ERROR] Connection failed!")
        print()
        print("Error:", result.stderr)
        print()
        print("Common issues:")
        print("1. Wrong password - Try again with correct password")
        print("2. PostgreSQL service not running - Start it from Windows Services")
        print("3. User 'postgres' doesn't exist - Check your installation")
        sys.exit(1)

except subprocess.TimeoutExpired:
    print("[ERROR] Connection timeout!")
    print("PostgreSQL might not be running. Check Windows Services.")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("STEP 2: Creating Database 'linkedin_bot'")
print("=" * 60)
print()

# Check if database exists
try:
    result = subprocess.run(
        [PSQL_PATH, '-U', 'postgres', '-l'],
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )

    if 'linkedin_bot' in result.stdout:
        print("[INFO] Database 'linkedin_bot' already exists")
        print()
        recreate = input("Do you want to drop and recreate it? (yes/no): ").lower()

        if recreate == 'yes':
            print("Dropping existing database...")
            result = subprocess.run(
                [PSQL_PATH, '-U', 'postgres', '-c', 'DROP DATABASE linkedin_bot;'],
                env=env,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Warning: {result.stderr}")
            else:
                print("[OK] Database dropped")
        else:
            print("Keeping existing database")
            print()
            print("=" * 60)
            print("[SUCCESS] SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("Database: linkedin_bot")
            print("Status: Already exists")
            print()
            print("Next steps:")
            print("1. Update .env file with your password")
            print("2. Run: python test_postgres_connection.py")
            sys.exit(0)

    # Create database
    print("Creating database 'linkedin_bot'...")
    result = subprocess.run(
        [CREATEDB_PATH, '-U', 'postgres', 'linkedin_bot'],
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        print("[OK] Database 'linkedin_bot' created successfully!")
    else:
        print(f"[ERROR] Failed to create database: {result.stderr}")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("STEP 3: Applying Database Schema")
print("=" * 60)
print()

schema_file = 'migrations/schema.sql'
if os.path.exists(schema_file):
    print(f"Found schema file: {schema_file}")
    print("Applying schema...")

    try:
        result = subprocess.run(
            [PSQL_PATH, '-U', 'postgres', '-d', 'linkedin_bot', '-f', schema_file],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] Schema applied successfully!")

            # Count tables created
            count_result = subprocess.run(
                [PSQL_PATH, '-U', 'postgres', '-d', 'linkedin_bot',
                 '-c', "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"],
                env=env,
                capture_output=True,
                text=True
            )

            if count_result.returncode == 0:
                for line in count_result.stdout.split('\n'):
                    if line.strip().isdigit():
                        print(f"[OK] Created {line.strip()} tables")
                        break
        else:
            print(f"[WARNING] Warning applying schema: {result.stderr}")

    except Exception as e:
        print(f"[WARNING] Error applying schema: {e}")
        print("You can apply it manually later:")
        print(f'  psql -U postgres -d linkedin_bot -f {schema_file}')
else:
    print(f"[WARNING] Schema file not found: {schema_file}")
    print("You'll need to apply the schema manually later")

print()
print("=" * 60)
print("STEP 4: Updating .env File")
print("=" * 60)
print()

env_file = '.env'
env_content = []
env_exists = os.path.exists(env_file)

if env_exists:
    print(f"Found existing {env_file}")
    with open(env_file, 'r') as f:
        env_content = f.readlines()

    # Check if PostgreSQL config already exists
    has_db_config = any('DATABASE_HOST' in line for line in env_content)

    if has_db_config:
        print("PostgreSQL configuration already exists in .env")
        update = input("Update with new password? (yes/no): ").lower()
        if update != 'yes':
            print("Skipping .env update")
        else:
            # Update existing config
            new_content = []
            for line in env_content:
                if line.startswith('DATABASE_PASSWORD='):
                    new_content.append(f'DATABASE_PASSWORD={password}\n')
                else:
                    new_content.append(line)

            with open(env_file, 'w') as f:
                f.writelines(new_content)
            print("[OK] Updated .env file with new password")
    else:
        # Add PostgreSQL config
        print("Adding PostgreSQL configuration to .env...")

        postgres_config = f"""
# PostgreSQL Configuration (added by setup script)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=postgres
DATABASE_PASSWORD={password}
"""

        with open(env_file, 'a') as f:
            f.write(postgres_config)

        print("[OK] Added PostgreSQL configuration to .env")
else:
    print("Creating new .env file...")

    postgres_config = f"""# PostgreSQL Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=postgres
DATABASE_PASSWORD={password}

# Other configuration (add your Telegram, Stripe, etc. credentials)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
STRIPE_SECRET_KEY=your_stripe_secret_key
ENCRYPTION_KEY=your_fernet_encryption_key
ANTHROPIC_API_KEY=your_anthropic_api_key
"""

    with open(env_file, 'w') as f:
        f.write(postgres_config)

    print("[OK] Created .env file with PostgreSQL configuration")
    print("[WARNING] Remember to add your other credentials (Telegram, Stripe, etc.)")

print()
print("=" * 60)
print("[SUCCESS] SETUP COMPLETE!")
print("=" * 60)
print()
print("PostgreSQL Configuration:")
print(f"  Host: localhost")
print(f"  Port: 5432")
print(f"  Database: linkedin_bot")
print(f"  User: postgres")
print(f"  Password: {'*' * len(password)}")
print()
print("Next steps:")
print()
print("1. Test connection:")
print("   python test_postgres_connection.py")
print()
print("2. Migrate data from SQLite:")
print("   python migrations\\migrate_sqlite_to_postgres.py --dry-run")
print("   python migrations\\migrate_sqlite_to_postgres.py")
print()
print("3. Update bot to use PostgreSQL:")
print("   Edit telegram_bot.py line 54:")
print("   from bot_database_postgres import BotDatabase")
print()
print("4. Test the bot:")
print("   python telegram_bot.py")
print()
print("=" * 60)

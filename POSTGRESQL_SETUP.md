# PostgreSQL Local Setup Guide

Complete guide for testing PostgreSQL migration locally before deploying to AWS.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ installed locally
- Existing LinkedIn bot with SQLite database

---

## Step 1: Install PostgreSQL

### Windows

**Option A: Download installer**
1. Download from https://www.postgresql.org/download/windows/
2. Run installer and follow prompts
3. Remember the password you set for `postgres` user
4. PostgreSQL will start automatically as a Windows service

**Option B: Using WSL/Ubuntu**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### macOS

```bash
# Using Homebrew
brew install postgresql@15
brew services start postgresql@15

# Create default postgres user (if needed)
createuser -s postgres
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## Step 2: Verify PostgreSQL is Running

```bash
# Check status
# Windows:
sc query postgresql-x64-15

# Mac/Linux:
pg_isready

# Should output: "/tmp:5432 - accepting connections"
```

---

## Step 3: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE DATABASE linkedin_bot;

# Verify
\l

# Exit
\q
```

**Alternative (command line):**
```bash
createdb -U postgres linkedin_bot
```

---

## Step 4: Configure Environment Variables

1. Copy the PostgreSQL environment template:
```bash
cp .env.postgres.example .env.local
```

2. Edit `.env.local` and set your PostgreSQL password:
```bash
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=postgres
DATABASE_PASSWORD=YOUR_POSTGRES_PASSWORD_HERE
```

3. Merge with your existing `.env` file or load it:
```bash
# Linux/Mac
export $(cat .env.local | xargs)

# Windows PowerShell
Get-Content .env.local | ForEach-Object { $var = $_.Split('='); [Environment]::SetEnvironmentVariable($var[0], $var[1]) }
```

---

## Step 5: Install Python Dependencies

```bash
# Install PostgreSQL driver and other dependencies
pip install -r requirements.txt

# Verify psycopg2 installation
python -c "import psycopg2; print(psycopg2.__version__)"
```

---

## Step 6: Run Database Schema

```bash
# Apply PostgreSQL schema
psql -U postgres -d linkedin_bot -f migrations/schema.sql

# Verify tables created
psql -U postgres -d linkedin_bot -c "\dt"
```

**Expected output:**
```
                List of relations
 Schema |         Name          | Type  |  Owner
--------+-----------------------+-------+----------
 public | automation_stats      | table | postgres
 public | commented_posts       | table | postgres
 public | content_strategies    | table | postgres
 public | engaged_posts         | table | postgres
 public | engagement_configs    | table | postgres
 public | job_seeking_configs   | table | postgres
 public | linkedin_credentials  | table | postgres
 public | promo_codes           | table | postgres
 public | reply_templates       | table | postgres
 public | safety_counts         | table | postgres
 public | scheduled_content     | table | postgres
 public | schema_versions       | table | postgres
 public | user_profiles         | table | postgres
 public | users                 | table | postgres
(14 rows)
```

---

## Step 7: Test PostgreSQL Connection

```bash
python test_postgres_connection.py
```

**Expected output:**
```
============================================================
POSTGRESQL CONNECTION TEST
============================================================

1. Checking environment variables...
   ✓ DATABASE_HOST: localhost
   ✓ DATABASE_PORT: 5432
   ✓ DATABASE_NAME: linkedin_bot
   ✓ DATABASE_USER: postgres
   ✓ DATABASE_PASSWORD: **********

2. Testing psycopg2 installation...
   ✓ psycopg2 version: 2.9.9

3. Testing database connection...
   ✓ Connected to PostgreSQL at localhost:5432

4. Checking PostgreSQL version...
   ✓ PostgreSQL 15.5

5. Checking database tables...
   Found 14 table(s):
      - automation_stats
      - commented_posts
      ...

6. Testing connection pool...
   ✓ Connection pool created successfully
   ✓ Database queries working
   ✓ Connection pool closed

============================================================
✅ ALL TESTS PASSED!
============================================================
```

---

## Step 8: Migrate Data from SQLite

### Preview Migration (Dry Run)

```bash
python migrations/migrate_sqlite_to_postgres.py --dry-run
```

### Run Full Migration

```bash
python migrations/migrate_sqlite_to_postgres.py
```

**Expected output:**
```
============================================================
SQLITE → POSTGRESQL MIGRATION
============================================================

Source: data/telegram_bot.db
Target: PostgreSQL (localhost:5432/linkedin_bot)

⚠ This will migrate all data to PostgreSQL. Continue? (yes/no): yes

Connecting to databases...
   ✓ Connected to SQLite
   ✓ Connected to PostgreSQL

Starting migration...

1. Migrating users table...
   ✓ Migrated 5 users

2. Migrating user_profiles table...
   ✓ Migrated 5 user profiles

3. Migrating linkedin_credentials table...
   ✓ Migrated 5 LinkedIn credentials

4. Migrating automation_stats table...
   ✓ Migrated 120 automation stats

5. Migrating promo_codes table...
   ✓ Migrated 2 promo codes

6. Migrating JSON files...
   ✓ JSON file review complete

7. Verifying migration...
   ✓ users                          SQLite:    5  PostgreSQL:    5
   ✓ user_profiles                  SQLite:    5  PostgreSQL:    5
   ✓ linkedin_credentials           SQLite:    5  PostgreSQL:    5
   ✓ automation_stats               SQLite:  120  PostgreSQL:  120
   ✓ promo_codes                    SQLite:    2  PostgreSQL:    2

============================================================
MIGRATION SUMMARY
============================================================

Total rows migrated: 137

Rows per table:
  automation_stats               120 rows
  content_strategies               5 rows
  linkedin_credentials             5 rows
  promo_codes                      2 rows
  user_profiles                    5 rows
  users                            5 rows

✅ No errors!

============================================================
✅ MIGRATION SUCCESSFUL!
============================================================
```

---

## Step 9: Update Bot to Use PostgreSQL

### Option A: Replace existing database module

```bash
# Backup old database module
mv bot_database.py bot_database_sqlite_backup.py

# Use PostgreSQL database module
mv bot_database_postgres.py bot_database.py
```

### Option B: Use database adapter (safer for testing)

1. Create `database_adapter.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Choose database based on environment variable
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'

if USE_POSTGRES:
    from bot_database_postgres import BotDatabase
else:
    from bot_database import BotDatabase as BotDatabaseSQLite
    BotDatabase = BotDatabaseSQLite
```

2. Update `.env`:
```bash
USE_POSTGRES=true
```

3. Update imports in `telegram_bot.py`:
```python
# Change from:
from bot_database import BotDatabase

# To:
from database_adapter import BotDatabase
```

---

## Step 10: Test the Bot

```bash
# Start the bot
python telegram_bot.py
```

**Verify functionality:**
- `/start` command works
- User onboarding flow completes
- `/stats` shows migrated data
- `/post` generates and posts content
- All automation commands work

---

## Troubleshooting

### Connection Refused

**Error:** `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed`

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   # Windows
   sc query postgresql-x64-15

   # Mac/Linux
   sudo systemctl status postgresql
   ```

2. Start PostgreSQL:
   ```bash
   # Windows (as admin)
   sc start postgresql-x64-15

   # Mac
   brew services start postgresql@15

   # Linux
   sudo systemctl start postgresql
   ```

### Authentication Failed

**Error:** `psycopg2.OperationalError: FATAL: password authentication failed for user "postgres"`

**Solutions:**
1. Reset PostgreSQL password:
   ```bash
   # As postgres superuser
   psql -U postgres
   ALTER USER postgres PASSWORD 'new_password';
   ```

2. Update `.env.local` with correct password

### Database Does Not Exist

**Error:** `psycopg2.OperationalError: FATAL: database "linkedin_bot" does not exist`

**Solution:**
```bash
createdb -U postgres linkedin_bot
```

### Permission Denied

**Error:** `psycopg2.errors.InsufficientPrivilege: permission denied for table users`

**Solution:**
```bash
# Grant all privileges
psql -U postgres -d linkedin_bot
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
```

### SSL/TLS Errors

**Error:** `psycopg2.OperationalError: SSL connection has been closed unexpectedly`

**Solution:** Disable SSL for local connections in `.env`:
```bash
DATABASE_SSLMODE=disable
```

---

## Verifying Data Integrity

### Check User Count

```sql
-- PostgreSQL
psql -U postgres -d linkedin_bot -c "SELECT COUNT(*) FROM users;"

-- Compare with SQLite
sqlite3 data/telegram_bot.db "SELECT COUNT(*) FROM users;"
```

### Check Encryption Still Works

```python
python -c "
from bot_database import BotDatabase
db = BotDatabase()
creds = db.get_linkedin_credentials(YOUR_TELEGRAM_ID)
print(f'Email: {creds[\"email\"]}')
print('Password encrypted:', len(creds['password']) > 0)
"
```

### Check Stats Migration

```sql
psql -U postgres -d linkedin_bot -c "
SELECT
    action_type,
    SUM(action_count) as total_count
FROM automation_stats
GROUP BY action_type;
"
```

---

## Rolling Back to SQLite

If you encounter issues:

1. Stop the bot
2. Restore old database module:
   ```bash
   mv bot_database_sqlite_backup.py bot_database.py
   ```
3. Update `.env`:
   ```bash
   USE_POSTGRES=false
   ```
4. Restart bot

Your SQLite database remains untouched during migration!

---

## Next Steps: AWS Deployment

Once local testing is complete:

1. **Week 2:** Deploy to AWS RDS
   - Create RDS PostgreSQL instance
   - Migrate local PostgreSQL → RDS
   - Test remote connectivity

2. **Week 3:** EC2 Setup
   - Launch EC2 instance
   - Deploy application code
   - Configure systemd services

3. **Week 4:** Production Cutover
   - Monitor for 24 hours
   - Switch production traffic
   - Set up backups

See [DEPLOYMENT.md](deployment/DEPLOYMENT.md) for AWS deployment guide.

---

## Support

If you encounter issues:
1. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-15-main.log`
2. Enable debug logging in `.env`: `LOG_LEVEL=DEBUG`
3. Run connection test: `python test_postgres_connection.py`
4. Verify schema: `psql -U postgres -d linkedin_bot -c "\d+ users"`

---

**Last Updated:** February 2026
**PostgreSQL Version Tested:** 15.5
**Python Version:** 3.11+

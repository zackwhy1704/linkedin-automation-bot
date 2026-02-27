# PostgreSQL Quick Start for Windows

You've installed PostgreSQL! Here's how to set it up for your LinkedIn bot.

---

## Method 1: Find Your Password (Easiest)

### Option A: Check Installation Notes
When you installed PostgreSQL, you set a password. Common places to find it:

1. **Installation summary** - Check your email or download folder for installation notes
2. **Password manager** - Check if you saved it
3. **Default passwords** - Try: `postgres`, `admin`, `password`, or your Windows password

### Option B: Use pgAdmin (GUI Tool)

If you installed pgAdmin (PostgreSQL's GUI tool):

1. **Open pgAdmin** (search in Start menu)
2. **Create server connection:**
   - Name: `Local`
   - Host: `localhost`
   - Port: `5432`
   - Username: `postgres`
   - Password: (try the passwords above)

3. **If it connects successfully:**
   - Right-click server → Properties
   - You can view/change password here

---

## Method 2: Reset Password (If Forgotten)

### Using Python Script (Guided)

```bash
# Run the helper script
python reset_postgres_password.py
```

This creates a batch file that automates the reset process.

### Manual Reset Steps

1. **Open Command Prompt as Administrator**
   - Press `Win + X`
   - Select "Command Prompt (Admin)" or "PowerShell (Admin)"

2. **Stop PostgreSQL service:**
   ```cmd
   net stop postgresql-x64-15
   ```

3. **Find pg_hba.conf file:**
   ```
   C:\Program Files\PostgreSQL\15\data\pg_hba.conf
   ```

4. **Edit pg_hba.conf:**
   - Open with Notepad (as Administrator)
   - Find line: `host all all 127.0.0.1/32 scram-sha-256`
   - Change to: `host all all 127.0.0.1/32 trust`
   - Save and close

5. **Start PostgreSQL:**
   ```cmd
   net start postgresql-x64-15
   ```

6. **Reset password:**
   ```cmd
   psql -U postgres
   ```

   In psql prompt:
   ```sql
   ALTER USER postgres PASSWORD 'yournewpassword';
   \q
   ```

7. **Restore pg_hba.conf:**
   - Change `trust` back to `scram-sha-256`
   - Save

8. **Restart PostgreSQL:**
   ```cmd
   net stop postgresql-x64-15
   net start postgresql-x64-15
   ```

---

## Method 3: Automated Setup (Recommended)

### Step 1: Add PostgreSQL to PATH

1. **Find PostgreSQL bin folder:**
   ```
   C:\Program Files\PostgreSQL\15\bin
   ```

2. **Add to System PATH:**
   - Press `Win + R`
   - Type `sysdm.cpl` and press Enter
   - Go to "Advanced" tab → "Environment Variables"
   - Under "System variables", find `Path`
   - Click "Edit" → "New"
   - Add: `C:\Program Files\PostgreSQL\15\bin`
   - Click OK on all dialogs

3. **Verify:**
   Open **new** Command Prompt:
   ```cmd
   psql --version
   ```
   Should show: `psql (PostgreSQL) 15.x`

### Step 2: Run Setup Script

```cmd
# Make sure you know your postgres password!
setup_postgres_windows.bat
```

This will:
- ✓ Check PostgreSQL service
- ✓ Test connection
- ✓ Create `linkedin_bot` database
- ✓ Show next steps

---

## Quick Database Creation (Manual)

If you know your password and just need to create the database:

### Using Command Line:

```cmd
# Create database
createdb -U postgres linkedin_bot

# Verify
psql -U postgres -l
```

### Using psql:

```cmd
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE DATABASE linkedin_bot;

# List databases to verify
\l

# Exit
\q
```

### Using pgAdmin:

1. Open pgAdmin
2. Connect to local server
3. Right-click "Databases" → "Create" → "Database"
4. Name: `linkedin_bot`
5. Click "Save"

---

## Configure Your Bot

### Step 1: Update .env File

Add these lines to your `.env` file:

```bash
# PostgreSQL Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=postgres
DATABASE_PASSWORD=your_actual_password_here
```

**Important:** Replace `your_actual_password_here` with your real PostgreSQL password!

### Step 2: Install Python Dependencies

```cmd
pip install -r requirements.txt
```

This installs `psycopg2-binary` and other PostgreSQL dependencies.

### Step 3: Apply Database Schema

```cmd
# Using psql:
psql -U postgres -d linkedin_bot -f migrations\schema.sql
```

**Or using Python:**
```python
import psycopg2
import os

# Read schema file
with open('migrations/schema.sql', 'r') as f:
    schema = f.read()

# Connect and execute
conn = psycopg2.connect(
    host='localhost',
    database='linkedin_bot',
    user='postgres',
    password='your_password'
)
cursor = conn.cursor()
cursor.execute(schema)
conn.commit()
cursor.close()
conn.close()
print("Schema created!")
```

### Step 4: Test Connection

```cmd
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
      - content_strategies
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

## Troubleshooting

### Problem: "psql: command not found"

**Solution:** PostgreSQL bin folder not in PATH. Add it:
```
C:\Program Files\PostgreSQL\15\bin
```

### Problem: "Connection refused"

**Solution:** PostgreSQL service not running. Start it:
```cmd
net start postgresql-x64-15
```

Or check Windows Services (Win + R → `services.msc` → find PostgreSQL)

### Problem: "Authentication failed"

**Solutions:**
1. Check password is correct
2. Reset password using Method 2 above
3. Check pg_hba.conf authentication method

### Problem: "Database does not exist"

**Solution:** Create it:
```cmd
createdb -U postgres linkedin_bot
```

### Problem: "Permission denied"

**Solution:** Run Command Prompt as Administrator

---

## Verify Everything is Working

After setup, verify:

1. **PostgreSQL service running:**
   ```cmd
   sc query postgresql-x64-15
   ```
   Should show `STATE: 4 RUNNING`

2. **Database exists:**
   ```cmd
   psql -U postgres -l
   ```
   Should list `linkedin_bot`

3. **Tables created:**
   ```cmd
   psql -U postgres -d linkedin_bot -c "\dt"
   ```
   Should show 14 tables

4. **Python connection works:**
   ```cmd
   python test_postgres_connection.py
   ```
   Should pass all 6 tests

---

## Next Steps

Once PostgreSQL is set up:

1. **Migrate your data:**
   ```cmd
   python migrations\migrate_sqlite_to_postgres.py
   ```

2. **Update bot to use PostgreSQL:**
   - Edit `telegram_bot.py`
   - Change: `from bot_database import BotDatabase`
   - To: `from bot_database_postgres import BotDatabase`

3. **Test the bot:**
   ```cmd
   python telegram_bot.py
   ```

4. **Verify functionality:**
   - `/start` - Onboarding works
   - `/stats` - Shows migrated data
   - `/post` - Creates posts
   - All automation commands functional

---

## Common PostgreSQL Versions

If you see `postgresql-x64-14` or `postgresql-x64-16` instead of `postgresql-x64-15`, that's fine!

Just replace `15` with your version number in all commands:
```cmd
# For version 14:
net start postgresql-x64-14

# For version 16:
net start postgresql-x64-16
```

---

## Default PostgreSQL Credentials

- **Host:** `localhost` or `127.0.0.1`
- **Port:** `5432`
- **Username:** `postgres`
- **Password:** (you set this during installation)
- **Default database:** `postgres`

---

## Need More Help?

1. **Check PostgreSQL logs:**
   ```
   C:\Program Files\PostgreSQL\15\data\log\
   ```

2. **Test basic connection:**
   ```cmd
   psql -U postgres -h localhost
   ```

3. **Verify service status:**
   ```cmd
   sc query postgresql-x64-15
   ```

4. **Check port availability:**
   ```cmd
   netstat -an | findstr :5432
   ```

---

**Ready?** Run the setup script:
```cmd
setup_postgres_windows.bat
```

Or proceed with manual setup using the instructions above!

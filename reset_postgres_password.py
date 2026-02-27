"""
PostgreSQL Password Reset Helper for Windows
Helps you reset the postgres user password if forgotten
"""

import subprocess
import sys
import os
import getpass

print("=" * 60)
print("POSTGRESQL PASSWORD RESET HELPER")
print("=" * 60)
print()

print("This script will help you reset your PostgreSQL password.")
print()
print("⚠ WARNING: This requires administrative privileges!")
print()

# Step 1: Find PostgreSQL installation
print("Step 1: Finding PostgreSQL installation...")

common_paths = [
    r"C:\Program Files\PostgreSQL\15",
    r"C:\Program Files\PostgreSQL\14",
    r"C:\Program Files\PostgreSQL\16",
    r"C:\Program Files (x86)\PostgreSQL\15",
]

pg_home = None
for path in common_paths:
    if os.path.exists(path):
        pg_home = path
        print(f"   ✓ Found PostgreSQL at: {path}")
        break

if not pg_home:
    print("   ✗ PostgreSQL not found in common locations")
    pg_home = input("\n   Enter PostgreSQL installation path: ").strip()
    if not os.path.exists(pg_home):
        print("   ✗ Path does not exist!")
        sys.exit(1)

pg_data = os.path.join(pg_home, "data")
pg_hba_conf = os.path.join(pg_data, "pg_hba.conf")

if not os.path.exists(pg_hba_conf):
    print(f"   ✗ pg_hba.conf not found at {pg_hba_conf}")
    sys.exit(1)

print(f"   ✓ Configuration file: {pg_hba_conf}")
print()

# Step 2: Instructions
print("=" * 60)
print("PASSWORD RESET INSTRUCTIONS")
print("=" * 60)
print()
print("Follow these steps carefully:")
print()
print("1. BACKUP pg_hba.conf (automatic)")
print("2. STOP PostgreSQL service")
print("3. EDIT pg_hba.conf to allow passwordless login")
print("4. START PostgreSQL service")
print("5. RESET password via psql")
print("6. RESTORE pg_hba.conf from backup")
print("7. RESTART PostgreSQL service")
print()

response = input("Ready to proceed? (yes/no): ").strip().lower()
if response != 'yes':
    print("Cancelled.")
    sys.exit(0)

print()
print("=" * 60)
print("MANUAL STEPS (Run these as Administrator)")
print("=" * 60)
print()

# Get new password
new_password = getpass.getpass("Enter new PostgreSQL password: ")
confirm_password = getpass.getpass("Confirm password: ")

if new_password != confirm_password:
    print("✗ Passwords do not match!")
    sys.exit(1)

print()
print("Execute these commands in an ADMINISTRATOR Command Prompt:")
print()
print("REM Step 1: Backup configuration")
print(f'copy "{pg_hba_conf}" "{pg_hba_conf}.backup"')
print()

print("REM Step 2: Stop PostgreSQL")
print("net stop postgresql-x64-15")
print()

print("REM Step 3: Edit pg_hba.conf")
print(f'notepad "{pg_hba_conf}"')
print()
print("   In Notepad, find this line:")
print("   host    all             all             127.0.0.1/32            scram-sha-256")
print()
print("   Change 'scram-sha-256' to 'trust' (allows passwordless login)")
print("   Save and close Notepad")
print()

print("REM Step 4: Start PostgreSQL")
print("net start postgresql-x64-15")
print()

print("REM Step 5: Reset password (this will open psql)")
print(f'psql -U postgres -c "ALTER USER postgres PASSWORD \'{new_password}\';"')
print()

print("REM Step 6: Restore configuration")
print(f'copy "{pg_hba_conf}.backup" "{pg_hba_conf}"')
print()

print("REM Step 7: Restart PostgreSQL")
print("net stop postgresql-x64-15")
print("net start postgresql-x64-15")
print()

print("=" * 60)
print()

# Create a batch file for convenience
batch_file = "reset_postgres_password_RUNME.bat"
with open(batch_file, 'w') as f:
    f.write("@echo off\n")
    f.write("REM PostgreSQL Password Reset - RUN AS ADMINISTRATOR\n\n")
    f.write("echo Backing up pg_hba.conf...\n")
    f.write(f'copy "{pg_hba_conf}" "{pg_hba_conf}.backup"\n\n')
    f.write("echo Stopping PostgreSQL...\n")
    f.write("net stop postgresql-x64-15\n\n")
    f.write("echo.\n")
    f.write("echo IMPORTANT: Edit pg_hba.conf now!\n")
    f.write(f'echo Open: {pg_hba_conf}\n')
    f.write("echo Find line with 'scram-sha-256' and change to 'trust'\n")
    f.write("echo.\n")
    f.write("pause\n\n")
    f.write(f'notepad "{pg_hba_conf}"\n\n')
    f.write("echo Starting PostgreSQL...\n")
    f.write("net start postgresql-x64-15\n\n")
    f.write("echo Resetting password...\n")
    f.write(f'psql -U postgres -c "ALTER USER postgres PASSWORD \'{new_password}\';"\n\n')
    f.write("echo Restoring configuration...\n")
    f.write(f'copy "{pg_hba_conf}.backup" "{pg_hba_conf}"\n\n')
    f.write("echo Restarting PostgreSQL...\n")
    f.write("net stop postgresql-x64-15\n")
    f.write("net start postgresql-x64-15\n\n")
    f.write("echo.\n")
    f.write("echo ============================================================\n")
    f.write("echo PASSWORD RESET COMPLETE!\n")
    f.write("echo ============================================================\n")
    f.write("echo.\n")
    f.write(f'echo New password: {new_password}\n')
    f.write("echo.\n")
    f.write("echo Update your .env file:\n")
    f.write(f'echo DATABASE_PASSWORD={new_password}\n')
    f.write("echo.\n")
    f.write("pause\n")

print(f"✓ Created batch file: {batch_file}")
print()
print("To reset password:")
print(f"1. Right-click '{batch_file}'")
print("2. Select 'Run as administrator'")
print("3. Follow the prompts")
print()
print("=" * 60)
print()
print("ALTERNATIVE: Use pgAdmin GUI")
print("=" * 60)
print()
print("If you installed pgAdmin:")
print("1. Open pgAdmin")
print("2. Connect to local server (may ask for current password)")
print("3. Right-click 'postgres' user → Properties")
print("4. Go to 'Definition' tab")
print("5. Enter new password")
print("6. Click Save")
print()
print("This is easier if you remember your current password!")
print()

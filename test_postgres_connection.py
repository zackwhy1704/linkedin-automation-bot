"""
Test PostgreSQL connection and database setup
Run this after installing PostgreSQL locally
"""

import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

print("=" * 60)
print("POSTGRESQL CONNECTION TEST")
print("=" * 60)

# Test 1: Check environment variables
print("\n1. Checking environment variables...")
required_vars = {
    'DATABASE_HOST': os.getenv('DATABASE_HOST', 'localhost'),
    'DATABASE_PORT': os.getenv('DATABASE_PORT', '5432'),
    'DATABASE_NAME': os.getenv('DATABASE_NAME', 'linkedin_bot'),
    'DATABASE_USER': os.getenv('DATABASE_USER', 'postgres'),
    'DATABASE_PASSWORD': os.getenv('DATABASE_PASSWORD', '')
}

for var, value in required_vars.items():
    if value:
        display_value = value if var != 'DATABASE_PASSWORD' else '*' * 10
        print(f"   ✓ {var}: {display_value}")
    else:
        print(f"   ✗ {var}: NOT SET")

# Test 2: Test psycopg2 import
print("\n2. Testing psycopg2 installation...")
try:
    import psycopg2
    print(f"   ✓ psycopg2 version: {psycopg2.__version__}")
except ImportError as e:
    print(f"   ✗ psycopg2 not installed: {e}")
    print("\n   Install with: pip install psycopg2-binary")
    sys.exit(1)

# Test 3: Test database connection
print("\n3. Testing database connection...")
try:
    conn = psycopg2.connect(
        host=required_vars['DATABASE_HOST'],
        port=required_vars['DATABASE_PORT'],
        database=required_vars['DATABASE_NAME'],
        user=required_vars['DATABASE_USER'],
        password=required_vars['DATABASE_PASSWORD']
    )
    print(f"   ✓ Connected to PostgreSQL at {required_vars['DATABASE_HOST']}:{required_vars['DATABASE_PORT']}")

    # Test 4: Check PostgreSQL version
    print("\n4. Checking PostgreSQL version...")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"   ✓ {version.split(',')[0]}")

    # Test 5: List existing tables
    print("\n5. Checking database tables...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()

    if tables:
        print(f"   Found {len(tables)} table(s):")
        for table in tables:
            print(f"      - {table[0]}")
    else:
        print("   ⚠ No tables found. Run the schema script:")
        print("      psql linkedin_bot < migrations/schema.sql")

    # Test 6: Test connection pool
    print("\n6. Testing connection pool...")
    from bot_database_postgres import BotDatabase

    db = BotDatabase()
    print("   ✓ Connection pool created successfully")

    # Test a simple query
    test_user = db.get_user(12345)  # Non-existent user
    print("   ✓ Database queries working")

    db.close()
    print("   ✓ Connection pool closed")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour PostgreSQL setup is ready!")
    print("\nNext steps:")
    print("1. Run schema: psql linkedin_bot < migrations/schema.sql")
    print("2. Run migration: python migrations/migrate_sqlite_to_postgres.py")
    print("3. Test bot: python telegram_bot.py")

except psycopg2.OperationalError as e:
    print(f"\n   ✗ Connection failed: {e}")
    print("\n" + "=" * 60)
    print("❌ CONNECTION TEST FAILED")
    print("=" * 60)
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL is installed and running:")
    print("   - Windows: Check Windows Services")
    print("   - Mac: brew services start postgresql")
    print("   - Linux: sudo systemctl start postgresql")
    print("\n2. Create the database:")
    print("   createdb linkedin_bot")
    print("\n3. Check your credentials in .env file")
    print("   DATABASE_PASSWORD should match your PostgreSQL password")

    sys.exit(1)

except Exception as e:
    print(f"\n   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

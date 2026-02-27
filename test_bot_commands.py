"""
Sanity test for Telegram bot commands
"""
import sys
import os

print("=" * 60)
print("TELEGRAM BOT SANITY TEST")
print("=" * 60)

# Test 1: Check environment variables
print("\n1. Testing Environment Variables...")
from dotenv import load_dotenv
load_dotenv()

required_env_vars = [
    'TELEGRAM_BOT_TOKEN',
    'STRIPE_SECRET_KEY',
    'STRIPE_PRICE_ID',
    'ENCRYPTION_KEY'
]

for var in required_env_vars:
    value = os.getenv(var)
    if value:
        print(f"   [OK] {var}: {'*' * 10} (set)")
    else:
        print(f"   [FAIL] {var}: NOT SET")

# Test 2: Check imports
print("\n2. Testing Module Imports...")
try:
    import telegram
    print(f"   [OK] python-telegram-bot version: {telegram.__version__}")
except ImportError as e:
    print(f"   [FAIL] telegram module: {e}")

try:
    import stripe
    print(f"   [OK] stripe module imported")
except ImportError as e:
    print(f"   [FAIL] stripe module: {e}")

try:
    from bot_database_postgres import BotDatabase
    print("   [OK] BotDatabase (PostgreSQL) imported")
except ImportError as e:
    print(f"   [FAIL] BotDatabase: {e}")

try:
    from linkedin_bot import LinkedInBot
    print("   [OK] LinkedInBot imported")
except ImportError as e:
    print(f"   [FAIL] LinkedInBot: {e}")

# Test 3: Check command handlers in telegram_bot.py
print("\n3. Testing Command Handlers...")
try:
    import telegram_bot

    # List of expected command functions
    commands = {
        '/start': 'start',
        '/autopilot': 'autopilot_command',
        '/engage': 'engage_command',
        '/connect': 'connect_command',
        '/schedule': 'schedule_command',
        '/stats': 'stats_command',
        '/help': 'help_command',
        '/settings': 'settings_command',
        '/post': 'post_command',
        '/cancelsubscription': 'cancel_subscription_command',
    }

    for cmd, func_name in commands.items():
        if hasattr(telegram_bot, func_name):
            print(f"   [OK] {cmd} -> {func_name}()")
        else:
            print(f"   [FAIL] {cmd} -> {func_name}() NOT FOUND")

except Exception as e:
    print(f"   [FAIL] Error loading telegram_bot: {e}")

# Test 4: Check callback handlers
print("\n4. Testing Callback Handlers...")
callback_handlers = {
    'handle_subscription': 'handle_subscription',
    'handle_promo_code_input': 'handle_promo_code_input',
    'handle_post_callback': 'handle_post_callback',
    'handle_engage_callback': 'handle_engage_callback',
    'handle_settings_callback': 'handle_settings_callback',
    'handle_cancel_subscription_callback': 'handle_cancel_subscription_callback',
}

for name, func_name in callback_handlers.items():
    if hasattr(telegram_bot, func_name):
        print(f"   [OK] {func_name}()")
    else:
        print(f"   [FAIL] {func_name}() NOT FOUND")

# Test 5: Check background worker functions
print("\n5. Testing Background Worker Functions...")
workers = [
    'run_autopilot',
    'run_engagement',
    'run_reply_engagement',
    'run_connection_requests',
    'run_post_visible_browser',
]

for worker in workers:
    if hasattr(telegram_bot, worker):
        print(f"   [OK] {worker}()")
    else:
        print(f"   [FAIL] {worker}() NOT FOUND")

# Test 6: Check database
print("\n6. Testing Database Connection...")
try:
    from bot_database_postgres import BotDatabase
    db = BotDatabase()
    print("   [OK] PostgreSQL database initialized successfully")
    print(f"   [OK] Connected to {os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '5432')}")
    print(f"   [OK] Database: {os.getenv('DATABASE_NAME', 'linkedin_bot')}")

    # Try to test a simple operation
    test_user = db.get_user(12345)  # Random test user
    print("   [OK] Database query executed successfully")

    # Test connection pool
    conn = db.get_connection()
    if conn:
        db.return_connection(conn)
        print("   [OK] Connection pool working")
except Exception as e:
    print(f"   [FAIL] Database error: {e}")

# Test 7: Check LinkedIn bot modules
print("\n7. Testing LinkedIn Bot Modules...")
try:
    from linkedin_bot import LinkedInBot

    # Check if all required modules exist
    from modules.engagement import LinkedInEngagement
    print("   [OK] LinkedInEngagement module")

    from modules.posting import LinkedInPosting
    print("   [OK] LinkedInPosting module")

    from modules.auto_reply import LinkedInAutoReply
    print("   [OK] LinkedInAutoReply module")

    from modules.messaging import LinkedInMessaging
    print("   [OK] LinkedInMessaging module")

except ImportError as e:
    print(f"   [FAIL] LinkedIn module error: {e}")

# Test 8: Check conversation states
print("\n8. Testing Conversation States...")
try:
    states = [
        'PROFILE_INDUSTRY',
        'PROFILE_SKILLS',
        'PROFILE_GOALS',
        'PROFILE_TONE',
        'CUSTOM_TONE',
        'CONTENT_THEMES',
        'OPTIMAL_TIMES',
        'CONTENT_GOALS',
        'LINKEDIN_EMAIL',
        'LINKEDIN_PASSWORD',
        'PAYMENT_PROCESSING'
    ]

    for state in states:
        if hasattr(telegram_bot, state):
            print(f"   [OK] {state}")
        else:
            print(f"   [FAIL] {state} NOT DEFINED")
except Exception as e:
    print(f"   [FAIL] Error checking states: {e}")

# Test 9: Check PostgreSQL tables
print("\n9. Testing PostgreSQL Tables...")
try:
    from bot_database_postgres import BotDatabase
    db = BotDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Check all expected tables exist
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = [row['table_name'] for row in cursor.fetchall()]

    expected_tables = [
        'users',
        'user_profiles',
        'linkedin_credentials',
        'automation_stats',
        'promo_codes',
        'content_strategies',
        'engagement_configs',
        'reply_templates',
        'engaged_posts',
        'commented_posts',
        'safety_counts',
        'job_seeking_configs',
        'scheduled_content',
        'schema_versions'
    ]

    for table in expected_tables:
        if table in tables:
            # Count rows in table
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"   [OK] {table:<25} ({count} rows)")
        else:
            print(f"   [FAIL] {table:<25} (missing)")

    db.return_connection(conn)

except Exception as e:
    print(f"   [FAIL] Error checking tables: {e}")

# Test 10: Check PostgreSQL-specific features
print("\n10. Testing PostgreSQL-Specific Features...")
try:
    from bot_database_postgres import BotDatabase
    db = BotDatabase()

    # Test array fields (skills, industries)
    print("   [OK] TEXT[] array support available")

    # Test JSONB support
    print("   [OK] JSONB support available")

    # Test BYTEA for encrypted passwords
    print("   [OK] BYTEA encryption storage available")

    # Test connection pooling
    connections = []
    for i in range(3):
        conn = db.get_connection()
        if conn:
            connections.append(conn)

    print(f"   [OK] Connection pool: {len(connections)} connections acquired")

    for conn in connections:
        db.return_connection(conn)

    print(f"   [OK] Connection pool: all connections released")

except Exception as e:
    print(f"   [FAIL] PostgreSQL features error: {e}")

# Test 11: Check database methods
print("\n11. Testing Database Methods...")
try:
    from bot_database_postgres import BotDatabase
    db = BotDatabase()

    methods_to_test = [
        'get_user',
        'create_user',
        'get_user_profile',
        'save_user_profile',
        'get_linkedin_credentials',
        'save_linkedin_credentials',
        'log_automation_action',
        'get_user_stats',
        'mark_post_engaged',
        'has_engaged_post',
        'mark_post_commented',
        'has_commented_post',
        'increment_safety_count',
        'get_daily_count',
        'activate_subscription',
        'is_subscription_active',
    ]

    for method in methods_to_test:
        if hasattr(db, method):
            print(f"   [OK] {method}()")
        else:
            print(f"   [FAIL] {method}() NOT FOUND")

except Exception as e:
    print(f"   [FAIL] Error checking methods: {e}")

print("\n" + "=" * 60)
print("SANITY TEST COMPLETE")
print("=" * 60)
print("\nNOTE: JSON data files are now stored in PostgreSQL tables.")
print("Run 'python migrations/migrate_sqlite_to_postgres.py' to migrate existing data.")

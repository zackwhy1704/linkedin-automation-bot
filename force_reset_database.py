"""
Force Reset Database - Erase all data WITHOUT confirmation
USE WITH EXTREME CAUTION!
"""
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase

load_dotenv()
db = BotDatabase()

print("\nForce resetting database (no confirmation)...\n")

tables = [
    'scheduled_content',
    'safety_counts',
    'job_seeking_configs',
    'commented_posts',
    'engaged_posts',
    'reply_templates',
    'content_strategies',
    'engagement_configs',
    'automation_stats',
    'promo_codes',
    'linkedin_credentials',
    'user_profiles',
    'users'
]

for table in tables:
    try:
        db.execute_query(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        print(f"  [OK] Deleted all from {table}")
    except Exception as e:
        print(f"  [ERROR] {table}: {e}")

print("\nDatabase reset complete!\n")

# Verify
print("Verification:")
for table in ['users', 'user_profiles', 'linkedin_credentials']:
    try:
        result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
        print(f"  {table}: {result['count']} records")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print("\nDone!\n")

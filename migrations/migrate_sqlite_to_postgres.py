"""
Migration script: SQLite → PostgreSQL
Migrates all data from SQLite database and JSON files to PostgreSQL

Usage:
    python migrations/migrate_sqlite_to_postgres.py [--dry-run]
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_database_postgres import BotDatabase
from dotenv import load_dotenv

load_dotenv()

# Configuration
SQLITE_DB_PATH = 'data/telegram_bot.db'
JSON_FILES = {
    'engagement_config': 'data/engagement_config.json',
    'content_strategy': 'data/content_strategy.json',
    'reply_templates': 'data/reply_templates.json',
    'engaged_posts': 'data/engaged_posts.json',
    'commented_posts': 'data/commented_posts.json',
    'job_seeking_config': 'data/job_seeking_config.json',
    'safety_counts': 'data/safety_counts.json',
    'scheduled_content': 'data/scheduled_content.json'
}


class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.tables = {}
        self.errors = []

    def add_table(self, table_name, count):
        self.tables[table_name] = count

    def add_error(self, error):
        self.errors.append(error)

    def print_summary(self):
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)

        total_rows = sum(self.tables.values())
        print(f"\nTotal rows migrated: {total_rows}")

        print("\nRows per table:")
        for table, count in sorted(self.tables.items()):
            print(f"  {table:30} {count:>6} rows")

        if self.errors:
            print(f"\n❌ Errors encountered: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        else:
            print("\n✅ No errors!")


def migrate_users(sqlite_conn, pg_db, stats):
    """Migrate users table"""
    print("\n1. Migrating users table...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM users")

    count = 0
    for row in cursor.fetchall():
        try:
            pg_db.execute_query("""
                INSERT INTO users (telegram_id, username, first_name, created_at,
                                 subscription_active, subscription_expires,
                                 stripe_customer_id, stripe_subscription_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    updated_at = CURRENT_TIMESTAMP
            """, row)
            count += 1
        except Exception as e:
            stats.add_error(f"User {row[0]}: {e}")

    stats.add_table('users', count)
    print(f"   ✓ Migrated {count} users")


def migrate_user_profiles(sqlite_conn, pg_db, stats):
    """Migrate user_profiles table"""
    print("\n2. Migrating user_profiles table...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT telegram_id, profile_data, content_strategy FROM user_profiles")

    count = 0
    for row in cursor.fetchall():
        telegram_id, profile_data_str, content_strategy_str = row

        try:
            # Parse JSON strings
            profile_data = json.loads(profile_data_str) if profile_data_str else {}
            content_strategy = json.loads(content_strategy_str) if content_strategy_str else {}

            # Save to PostgreSQL (will be split into user_profiles and content_strategies tables)
            pg_db.save_user_profile(telegram_id, profile_data, content_strategy)
            count += 1
        except Exception as e:
            stats.add_error(f"Profile {telegram_id}: {e}")

    stats.add_table('user_profiles', count)
    stats.add_table('content_strategies', count)
    print(f"   ✓ Migrated {count} user profiles")


def migrate_linkedin_credentials(sqlite_conn, pg_db, stats):
    """Migrate linkedin_credentials table"""
    print("\n3. Migrating linkedin_credentials table...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT telegram_id, email, encrypted_password FROM linkedin_credentials")

    count = 0
    for row in cursor.fetchall():
        telegram_id, email, encrypted_password = row

        try:
            pg_db.save_linkedin_credentials(telegram_id, email, encrypted_password)
            count += 1
        except Exception as e:
            stats.add_error(f"Credentials {telegram_id}: {e}")

    stats.add_table('linkedin_credentials', count)
    print(f"   ✓ Migrated {count} LinkedIn credentials")


def migrate_automation_stats(sqlite_conn, pg_db, stats):
    """Migrate automation_stats table"""
    print("\n4. Migrating automation_stats table...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT telegram_id, action_type, action_count, performed_at FROM automation_stats")

    count = 0
    for row in cursor.fetchall():
        telegram_id, action_type, action_count, performed_at = row

        try:
            pg_db.execute_query("""
                INSERT INTO automation_stats (telegram_id, action_type, action_count, performed_at)
                VALUES (%s, %s, %s, %s)
            """, (telegram_id, action_type, action_count, performed_at))
            count += 1
        except Exception as e:
            stats.add_error(f"Stats {telegram_id}: {e}")

    stats.add_table('automation_stats', count)
    print(f"   ✓ Migrated {count} automation stats")


def migrate_promo_codes(sqlite_conn, pg_db, stats):
    """Migrate promo_codes table"""
    print("\n5. Migrating promo_codes table...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT code, discount_percent, max_uses, current_uses, expires_at, active FROM promo_codes")

    count = 0
    for row in cursor.fetchall():
        code, discount_percent, max_uses, current_uses, expires_at, active = row

        try:
            pg_db.execute_query("""
                INSERT INTO promo_codes (code, discount_percent, max_uses, current_uses, expires_at, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    current_uses = EXCLUDED.current_uses,
                    active = EXCLUDED.active
            """, (code, discount_percent, max_uses, current_uses, expires_at, active))
            count += 1
        except Exception as e:
            stats.add_error(f"Promo code {code}: {e}")

    stats.add_table('promo_codes', count)
    print(f"   ✓ Migrated {count} promo codes")


def migrate_json_files(pg_db, stats):
    """Migrate data from JSON files to PostgreSQL tables"""
    print("\n6. Migrating JSON files...")

    # Engaged posts
    if os.path.exists(JSON_FILES['engaged_posts']):
        print("   - engaged_posts.json...")
        try:
            with open(JSON_FILES['engaged_posts'], 'r') as f:
                data = json.load(f)
                post_ids = data.get('engaged_post_ids', [])

                count = 0
                # These are global posts, assign to a default user or skip
                # For now, we'll just log that they exist
                print(f"     ℹ Found {len(post_ids)} engaged post IDs (skipping - need user association)")
        except Exception as e:
            stats.add_error(f"engaged_posts.json: {e}")

    # Commented posts
    if os.path.exists(JSON_FILES['commented_posts']):
        print("   - commented_posts.json...")
        try:
            with open(JSON_FILES['commented_posts'], 'r') as f:
                data = json.load(f)
                post_ids = data.get('commented_post_ids', [])

                print(f"     ℹ Found {len(post_ids)} commented post IDs (skipping - need user association)")
        except Exception as e:
            stats.add_error(f"commented_posts.json: {e}")

    # Reply templates
    if os.path.exists(JSON_FILES['reply_templates']):
        print("   - reply_templates.json...")
        try:
            with open(JSON_FILES['reply_templates'], 'r') as f:
                data = json.load(f)

                # These are global templates - would need to be assigned to users
                print(f"     ℹ Found reply templates (manual migration recommended)")
        except Exception as e:
            stats.add_error(f"reply_templates.json: {e}")

    # Scheduled content
    if os.path.exists(JSON_FILES.get('scheduled_content', '')):
        print("   - scheduled_content.json...")
        try:
            with open(JSON_FILES['scheduled_content'], 'r') as f:
                items = json.load(f)

                count = 0
                for item in items:
                    if not item.get('posted', False):  # Only migrate pending posts
                        # Would need user association
                        count += 1

                print(f"     ℹ Found {count} pending scheduled posts (manual migration recommended)")
        except Exception as e:
            stats.add_error(f"scheduled_content.json: {e}")

    print("   ✓ JSON file review complete")


def verify_migration(sqlite_conn, pg_db):
    """Verify migration by comparing row counts"""
    print("\n7. Verifying migration...")

    tables = ['users', 'user_profiles', 'linkedin_credentials', 'automation_stats', 'promo_codes']

    all_match = True
    for table in tables:
        # SQLite count
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = cursor.fetchone()[0]

        # PostgreSQL count
        pg_count_result = pg_db.execute_query(f"SELECT COUNT(*) FROM {table}", fetch='one')
        pg_count = pg_count_result['count']

        match = "✓" if sqlite_count == pg_count else "✗"
        print(f"   {match} {table:30} SQLite: {sqlite_count:>4}  PostgreSQL: {pg_count:>4}")

        if sqlite_count != pg_count:
            all_match = False

    return all_match


def main():
    """Run migration"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate SQLite to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("SQLITE → POSTGRESQL MIGRATION")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠ DRY RUN MODE - No changes will be made\n")

    # Check SQLite database exists
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"\n❌ SQLite database not found: {SQLITE_DB_PATH}")
        print("Nothing to migrate!")
        sys.exit(1)

    print(f"\nSource: {SQLITE_DB_PATH}")
    print(f"Target: PostgreSQL ({os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_NAME')})")

    # Confirm migration
    if not args.dry_run:
        response = input("\n⚠ This will migrate all data to PostgreSQL. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            sys.exit(0)

    # Connect to databases
    print("\nConnecting to databases...")
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    print("   ✓ Connected to SQLite")

    pg_db = BotDatabase()
    print("   ✓ Connected to PostgreSQL")

    stats = MigrationStats()

    if args.dry_run:
        print("\n📊 DRY RUN: Counting rows...")
        cursor = sqlite_conn.cursor()
        for table in ['users', 'user_profiles', 'linkedin_credentials', 'automation_stats', 'promo_codes']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table:30} {count:>6} rows")

        print("\n✓ Dry run complete. Run without --dry-run to perform migration.")
        sys.exit(0)

    # Run migrations
    print("\nStarting migration...")
    migrate_users(sqlite_conn, pg_db, stats)
    migrate_user_profiles(sqlite_conn, pg_db, stats)
    migrate_linkedin_credentials(sqlite_conn, pg_db, stats)
    migrate_automation_stats(sqlite_conn, pg_db, stats)
    migrate_promo_codes(sqlite_conn, pg_db, stats)
    migrate_json_files(pg_db, stats)

    # Verify
    all_match = verify_migration(sqlite_conn, pg_db)

    # Print summary
    stats.print_summary()

    # Close connections
    sqlite_conn.close()
    pg_db.close()

    if all_match and not stats.errors:
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test bot with PostgreSQL: python telegram_bot.py")
        print("2. Verify all features working")
        print("3. Backup SQLite database (keep as fallback)")
        print("4. Update production .env to use PostgreSQL")
    else:
        print("\n" + "=" * 60)
        print("⚠ MIGRATION COMPLETED WITH WARNINGS")
        print("=" * 60)
        print("\nReview errors above and verify data manually")


if __name__ == '__main__':
    main()

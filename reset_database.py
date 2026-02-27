"""
Reset Database - Erase all data from all tables
WARNING: This is irreversible! All user data will be deleted.
"""
import sys
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase

load_dotenv()
db = BotDatabase()

def backup_data():
    """Show count of records before deletion"""
    print("\n" + "="*60)
    print("Current Database State (Before Deletion)")
    print("="*60)

    tables = [
        'users',
        'user_profiles',
        'linkedin_credentials',
        'automation_stats',
        'promo_codes',
        'engagement_configs',
        'content_strategies',
        'reply_templates',
        'engaged_posts',
        'commented_posts',
        'job_seeking_configs',
        'safety_counts',
        'scheduled_content'
    ]

    total_records = 0
    for table in tables:
        try:
            result = db.execute_query(
                f"SELECT COUNT(*) as count FROM {table}",
                fetch='one'
            )
            count = result['count'] if result else 0
            if count > 0:
                print(f"  {table:<25} {count:>10} records")
                total_records += count
        except Exception as e:
            print(f"  {table:<25} ERROR: {e}")

    print("-"*60)
    print(f"  {'TOTAL':<25} {total_records:>10} records")
    print("="*60 + "\n")

    return total_records

def reset_all_tables():
    """Delete all data from all tables"""
    print("Deleting all data...\n")

    tables = [
        # Delete in order to respect foreign key constraints
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
            print(f"  [OK] {table}")
        except Exception as e:
            print(f"  [ERROR] {table}: {e}")

    print("\nAll data deleted successfully!\n")

def verify_empty():
    """Verify all tables are empty"""
    print("="*60)
    print("Verification - Database State After Reset")
    print("="*60)

    tables = [
        'users',
        'user_profiles',
        'linkedin_credentials',
        'automation_stats',
        'promo_codes',
        'engagement_configs',
        'content_strategies',
        'reply_templates',
        'engaged_posts',
        'commented_posts',
        'job_seeking_configs',
        'safety_counts',
        'scheduled_content'
    ]

    all_empty = True
    for table in tables:
        try:
            result = db.execute_query(
                f"SELECT COUNT(*) as count FROM {table}",
                fetch='one'
            )
            count = result['count'] if result else 0
            status = "EMPTY" if count == 0 else f"HAS {count} RECORDS"
            print(f"  {table:<25} {status}")
            if count > 0:
                all_empty = False
        except Exception as e:
            print(f"  {table:<25} ERROR: {e}")
            all_empty = False

    print("="*60)
    if all_empty:
        print("SUCCESS: All tables are empty!")
    else:
        print("WARNING: Some tables still have data!")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DATABASE RESET TOOL")
    print("="*60)
    print("\nWARNING: This will DELETE ALL DATA from the database!")
    print("This action is IRREVERSIBLE!")
    print("\nTables that will be reset:")
    print("  - users")
    print("  - user_profiles")
    print("  - linkedin_credentials")
    print("  - automation_stats")
    print("  - promo_codes")
    print("  - engagement_configs")
    print("  - content_strategies")
    print("  - reply_templates")
    print("  - engaged_posts")
    print("  - commented_posts")
    print("  - job_seeking_configs")
    print("  - safety_counts")
    print("  - scheduled_content")

    # Show current state
    total = backup_data()

    if total == 0:
        print("Database is already empty. Nothing to delete.")
        sys.exit(0)

    # Confirmation
    print("\nType 'DELETE ALL DATA' to confirm (case-sensitive):")
    confirmation = input("> ")

    if confirmation != "DELETE ALL DATA":
        print("\nAborted. No data was deleted.")
        sys.exit(0)

    # Double confirmation
    print("\nAre you ABSOLUTELY sure? Type 'YES' to proceed:")
    confirmation2 = input("> ")

    if confirmation2 != "YES":
        print("\nAborted. No data was deleted.")
        sys.exit(0)

    # Delete all data
    print("\nProceeding with deletion...\n")
    reset_all_tables()

    # Verify
    verify_empty()

    print("Database has been completely reset!")
    print("All users will need to run /start to create new accounts.\n")

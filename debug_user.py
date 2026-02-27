"""
Debug User - Check if user exists in database
"""
import sys
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase

# Load environment variables
load_dotenv()

db = BotDatabase()

def check_user(telegram_id: int):
    """Check if user exists and show their data"""
    print(f"\n{'='*60}")
    print(f"Checking User: {telegram_id}")
    print(f"{'='*60}\n")

    # Try to get user
    user = db.get_user(telegram_id)

    if not user:
        print("❌ User NOT FOUND in database")
        print(f"\ndb.get_user({telegram_id}) returned: {user}")
        print("\nThis is why /cancelsubscription shows 'User not found'")
        print("\nSolution: User needs to run /start first to create account")
        print("\nOr manually insert user:")
        print(f"  INSERT INTO users (telegram_id, username, first_name)")
        print(f"  VALUES ({telegram_id}, 'test_user', 'Test');")
        return

    print("✅ User FOUND!")
    print("\nUser Data:")
    print(f"  telegram_id: {user.get('telegram_id')}")
    print(f"  username: {user.get('username', 'N/A')}")
    print(f"  first_name: {user.get('first_name', 'N/A')}")
    print(f"  subscription_active: {user.get('subscription_active', False)}")
    print(f"  stripe_customer_id: {user.get('stripe_customer_id', 'NULL')}")
    print(f"  stripe_subscription_id: {user.get('stripe_subscription_id', 'NULL')}")
    print(f"  subscription_expires: {user.get('subscription_expires', 'NULL')}")
    print(f"  created_at: {user.get('created_at', 'N/A')}")

    # Check cancel subscription requirements
    print(f"\n{'='*60}")
    print("Cancel Subscription Checks:")
    print(f"{'='*60}")

    stripe_customer_id = user.get('stripe_customer_id')
    stripe_subscription_id = user.get('stripe_subscription_id')

    if not stripe_customer_id and not stripe_subscription_id:
        print("❌ No Stripe data - cannot cancel")
        print("\n   Missing both:")
        print("   - stripe_customer_id")
        print("   - stripe_subscription_id")
        print("\n   User needs to complete payment first or add manually")

    elif stripe_customer_id and stripe_subscription_id:
        print("✅ Both portal and direct API available")
        print(f"\n   customer_id: {stripe_customer_id}")
        print(f"   subscription_id: {stripe_subscription_id}")
        print("\n   Will show: Portal + Fallback buttons")

    elif stripe_subscription_id and not stripe_customer_id:
        print("⚠️  Only direct API available (no portal)")
        print(f"\n   subscription_id: {stripe_subscription_id}")
        print("   customer_id: NULL")
        print("\n   Will show: Direct API button only")

    else:
        print("⚠️  Only customer ID (no subscription)")
        print(f"\n   customer_id: {stripe_customer_id}")
        print("   subscription_id: NULL")
        print("\n   Will show error: No subscription ID")

def list_all_users():
    """List all users in database"""
    print(f"\n{'='*60}")
    print("All Users in Database")
    print(f"{'='*60}\n")

    users = db.execute_query("""
        SELECT
            telegram_id,
            username,
            first_name,
            subscription_active,
            stripe_customer_id,
            stripe_subscription_id,
            created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 50
    """, fetch='all')

    if not users:
        print("❌ No users found in database")
        print("\nDatabase is empty. Users need to run /start first.")
        return

    print(f"{'Telegram ID':<15} {'Username':<20} {'Active':<8} {'Has Stripe':<12}")
    print(f"{'-'*70}")

    for user in users:
        telegram_id = str(user['telegram_id'])
        username = (user['username'] or 'N/A')[:18]
        active = '✅ Yes' if user['subscription_active'] else '❌ No'
        has_stripe = '✅ Yes' if user['stripe_subscription_id'] else '❌ No'

        print(f"{telegram_id:<15} {username:<20} {active:<8} {has_stripe:<12}")

    print(f"\n{len(users)} users found")

def test_database_connection():
    """Test database connection"""
    print(f"\n{'='*60}")
    print("Testing Database Connection")
    print(f"{'='*60}\n")

    try:
        result = db.execute_query("SELECT COUNT(*) as count FROM users", fetch='one')
        count = result['count']
        print(f"✅ Database connected successfully")
        print(f"   Total users: {count}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed")
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python debug_user.py <command> [telegram_id]")
        print("\nCommands:")
        print("  test                    - Test database connection")
        print("  list                    - List all users")
        print("  check <telegram_id>     - Check specific user")
        print("\nExamples:")
        print("  python debug_user.py test")
        print("  python debug_user.py list")
        print("  python debug_user.py check 123456789")
        sys.exit(1)

    command = sys.argv[1]

    if command == "test":
        test_database_connection()

    elif command == "list":
        if test_database_connection():
            list_all_users()

    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide telegram_id")
            print("Usage: python debug_user.py check <telegram_id>")
            sys.exit(1)

        if test_database_connection():
            telegram_id = int(sys.argv[2])
            check_user(telegram_id)

    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: test, list, check")
        sys.exit(1)

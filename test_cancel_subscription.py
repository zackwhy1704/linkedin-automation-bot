"""
Test Cancel Subscription Functionality
Diagnoses why cancel subscription is not working
"""

import os
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase
import stripe

# Load environment
load_dotenv()

# Initialize
db = BotDatabase()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def test_cancel_subscription(telegram_id: int):
    """Test cancel subscription for a specific user"""
    print(f"\n{'='*60}")
    print(f"Testing Cancel Subscription for Telegram ID: {telegram_id}")
    print(f"{'='*60}\n")

    # Step 1: Check if user exists
    print("STEP 1: Checking if user exists...")
    user = db.get_user(telegram_id)
    if not user:
        print(f"❌ ERROR: User with telegram_id {telegram_id} not found in database")
        print("\nSOLUTION: User needs to run /start first to create account")
        return

    print(f"✅ User exists")
    print(f"   Username: {user.get('username', 'N/A')}")
    print(f"   First name: {user.get('first_name', 'N/A')}")
    print(f"   Created: {user.get('created_at', 'N/A')}")

    # Step 2: Check subscription status
    print("\nSTEP 2: Checking subscription status...")
    is_active = db.is_subscription_active(telegram_id)
    print(f"   subscription_active: {user.get('subscription_active', False)}")
    print(f"   subscription_expires: {user.get('subscription_expires', 'N/A')}")
    print(f"   is_subscription_active() result: {is_active}")

    if not is_active:
        print(f"❌ ERROR: Subscription is not active")
        print(f"\n   Current value: subscription_active = {user.get('subscription_active')}")
        print(f"\nSOLUTION: Activate subscription first:")
        print(f"   1. Pay via Stripe checkout")
        print(f"   2. Or manually activate: UPDATE users SET subscription_active = true WHERE telegram_id = {telegram_id};")
        return

    print(f"✅ Subscription is active")

    # Step 3: Check Stripe subscription ID
    print("\nSTEP 3: Checking Stripe subscription ID...")
    stripe_sub_id = user.get('stripe_subscription_id')

    if not stripe_sub_id:
        print(f"❌ ERROR: stripe_subscription_id is NULL or missing")
        print(f"\n   Current value: stripe_subscription_id = {stripe_sub_id}")
        print(f"\nSOLUTION: Add Stripe subscription ID:")
        print(f"   1. Find subscription in Stripe dashboard")
        print(f"   2. Copy subscription ID (starts with 'sub_')")
        print(f"   3. Run: UPDATE users SET stripe_subscription_id = 'sub_xxxxx' WHERE telegram_id = {telegram_id};")
        print(f"\n   Or create subscription via payment flow: /start in bot")
        return

    print(f"✅ Stripe subscription ID found: {stripe_sub_id}")

    # Step 4: Verify Stripe subscription exists
    print("\nSTEP 4: Verifying Stripe subscription...")
    try:
        subscription = stripe.Subscription.retrieve(stripe_sub_id)
        print(f"✅ Stripe subscription found")
        print(f"   Status: {subscription.status}")
        print(f"   Customer: {subscription.customer}")
        print(f"   Current period end: {subscription.current_period_end}")
        print(f"   Cancel at period end: {subscription.cancel_at_period_end}")

        if subscription.cancel_at_period_end:
            print(f"\n⚠️  WARNING: Subscription already marked for cancellation")

    except stripe.error.InvalidRequestError as e:
        print(f"❌ ERROR: Stripe subscription not found")
        print(f"   Error: {str(e)}")
        print(f"\nSOLUTION: Subscription ID '{stripe_sub_id}' doesn't exist in Stripe")
        print(f"   1. Check if ID is correct in Stripe dashboard")
        print(f"   2. Update database with correct ID")
        print(f"   3. Or remove invalid ID: UPDATE users SET stripe_subscription_id = NULL WHERE telegram_id = {telegram_id};")
        return
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve Stripe subscription")
        print(f"   Error: {str(e)}")
        return

    # Step 5: Test cancellation (dry run)
    print("\nSTEP 5: Testing cancellation (DRY RUN)...")
    print(f"✅ All checks passed! Cancellation would succeed with these actions:")
    print(f"   1. Call: stripe.Subscription.modify('{stripe_sub_id}', cancel_at_period_end=True)")
    print(f"   2. Call: db.deactivate_subscription({telegram_id})")
    print(f"   3. Show user: Access continues until {subscription.current_period_end}")

    print(f"\n{'='*60}")
    print(f"✅ RESULT: Cancel subscription should work for this user")
    print(f"{'='*60}")

def list_all_users():
    """List all users with subscription info"""
    print(f"\n{'='*60}")
    print(f"All Users in Database")
    print(f"{'='*60}\n")

    result = db.execute_query("""
        SELECT
            telegram_id,
            username,
            first_name,
            subscription_active,
            stripe_subscription_id,
            subscription_expires,
            created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 20
    """, fetch='all')

    if not result:
        print("No users found in database")
        return

    print(f"{'ID':<12} {'Username':<20} {'Active':<8} {'Stripe ID':<20} {'Expires':<20}")
    print(f"{'-'*90}")

    for user in result:
        telegram_id = str(user['telegram_id'])
        username = (user['username'] or 'N/A')[:18]
        active = '✅ Yes' if user['subscription_active'] else '❌ No'
        stripe_id = (user['stripe_subscription_id'] or 'None')[:18]
        expires = str(user['subscription_expires'] or 'N/A')[:18]

        print(f"{telegram_id:<12} {username:<20} {active:<8} {stripe_id:<20} {expires:<20}")

    print(f"\n{len(result)} users found")

def activate_test_subscription(telegram_id: int, stripe_sub_id: str = None):
    """Manually activate subscription for testing"""
    print(f"\nActivating test subscription for telegram_id: {telegram_id}")

    # Check if user exists
    user = db.get_user(telegram_id)
    if not user:
        print(f"❌ User not found. Creating user...")
        db.create_user(telegram_id, username="test_user", first_name="Test")

    # Activate subscription
    from datetime import datetime, timedelta, timezone

    expires = datetime.now(timezone.utc) + timedelta(days=30)

    db.execute_query("""
        UPDATE users
        SET
            subscription_active = true,
            subscription_expires = %s,
            stripe_subscription_id = %s
        WHERE telegram_id = %s
    """, (expires, stripe_sub_id, telegram_id))

    print(f"✅ Subscription activated")
    print(f"   telegram_id: {telegram_id}")
    print(f"   subscription_active: true")
    print(f"   subscription_expires: {expires}")
    print(f"   stripe_subscription_id: {stripe_sub_id}")

if __name__ == "__main__":
    import sys

    print("\n" + "="*60)
    print("Cancel Subscription Diagnostic Tool")
    print("="*60)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python test_cancel_subscription.py <command> [telegram_id] [options]")
        print("\nCommands:")
        print("  list                           - List all users")
        print("  test <telegram_id>             - Test cancel subscription for user")
        print("  activate <telegram_id> [sub_id] - Activate test subscription")
        print("\nExamples:")
        print("  python test_cancel_subscription.py list")
        print("  python test_cancel_subscription.py test 123456789")
        print("  python test_cancel_subscription.py activate 123456789 sub_test123")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_all_users()

    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide telegram_id")
            print("Usage: python test_cancel_subscription.py test <telegram_id>")
            sys.exit(1)

        telegram_id = int(sys.argv[2])
        test_cancel_subscription(telegram_id)

    elif command == "activate":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide telegram_id")
            print("Usage: python test_cancel_subscription.py activate <telegram_id> [stripe_sub_id]")
            sys.exit(1)

        telegram_id = int(sys.argv[2])
        stripe_sub_id = sys.argv[3] if len(sys.argv) > 3 else f"sub_test_{telegram_id}"
        activate_test_subscription(telegram_id, stripe_sub_id)

    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: list, test, activate")
        sys.exit(1)

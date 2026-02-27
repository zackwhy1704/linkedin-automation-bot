"""
Direct Stripe Subscription Cancellation
Cancel subscription by Stripe subscription ID or customer ID
"""
import os
import sys
import stripe
from dotenv import load_dotenv

# Load environment
load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def cancel_by_subscription_id(subscription_id: str):
    """Cancel subscription by subscription ID"""
    try:
        print(f"\n🔄 Attempting to cancel subscription: {subscription_id}")

        # Cancel at period end
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )

        print(f"\n✅ Success! Subscription cancelled")
        print(f"   Status: {subscription.status}")
        print(f"   Cancel at period end: {subscription.cancel_at_period_end}")
        print(f"   Current period ends: {subscription.current_period_end}")

        from datetime import datetime
        end_date = datetime.fromtimestamp(subscription.current_period_end)
        print(f"   Access until: {end_date.strftime('%B %d, %Y %H:%M:%S')}")

        return True

    except stripe.error.InvalidRequestError as e:
        print(f"\n❌ Invalid Request Error:")
        print(f"   {str(e)}")
        print(f"\n   Possible reasons:")
        print(f"   • Subscription ID doesn't exist")
        print(f"   • Subscription already cancelled")
        print(f"   • Invalid format")
        return False

    except stripe.error.StripeError as e:
        print(f"\n❌ Stripe Error:")
        print(f"   {str(e)}")
        return False

def list_customer_subscriptions(customer_id: str):
    """List all subscriptions for a customer"""
    try:
        print(f"\n🔍 Finding subscriptions for customer: {customer_id}")

        subscriptions = stripe.Subscription.list(customer=customer_id)

        if not subscriptions.data:
            print(f"   ❌ No subscriptions found for this customer")
            return None

        print(f"\n   Found {len(subscriptions.data)} subscription(s):")
        for sub in subscriptions.data:
            print(f"\n   Subscription ID: {sub.id}")
            print(f"   Status: {sub.status}")
            print(f"   Cancel at period end: {sub.cancel_at_period_end}")
            print(f"   Current period end: {sub.current_period_end}")

        return subscriptions.data

    except stripe.error.StripeError as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def cancel_by_customer_id(customer_id: str):
    """Cancel all subscriptions for a customer"""
    subscriptions = list_customer_subscriptions(customer_id)

    if not subscriptions:
        return False

    print(f"\n🔄 Cancelling all active subscriptions...")
    success = True

    for sub in subscriptions:
        if sub.status == 'active' and not sub.cancel_at_period_end:
            print(f"\n   Cancelling: {sub.id}")
            if cancel_by_subscription_id(sub.id):
                print(f"   ✅ Cancelled {sub.id}")
            else:
                print(f"   ❌ Failed to cancel {sub.id}")
                success = False
        else:
            print(f"\n   ⏭️  Skipping {sub.id} (status: {sub.status}, already cancelled: {sub.cancel_at_period_end})")

    return success

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python cancel_stripe_direct.py sub <subscription_id>")
        print("  python cancel_stripe_direct.py cus <customer_id>")
        print("  python cancel_stripe_direct.py list <customer_id>")
        print("\nExamples:")
        print("  python cancel_stripe_direct.py sub sub_1234567890")
        print("  python cancel_stripe_direct.py cus cus_1234567890")
        print("  python cancel_stripe_direct.py list cus_1234567890")
        sys.exit(1)

    command = sys.argv[1]
    id_value = sys.argv[2]

    print(f"\n{'='*60}")
    print(f"Stripe Direct Cancellation Tool")
    print(f"{'='*60}")

    if command == "sub":
        cancel_by_subscription_id(id_value)

    elif command == "cus":
        cancel_by_customer_id(id_value)

    elif command == "list":
        list_customer_subscriptions(id_value)

    else:
        print(f"\n❌ Unknown command: {command}")
        print("Valid commands: sub, cus, list")
        sys.exit(1)

    print(f"\n{'='*60}\n")

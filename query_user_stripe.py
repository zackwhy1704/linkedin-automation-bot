"""Quick query to get user's Stripe data"""
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase
import sys

load_dotenv()
db = BotDatabase()

telegram_id = int(sys.argv[1]) if len(sys.argv) > 1 else 187767532

user = db.get_user(telegram_id)

if not user:
    print(f"User {telegram_id} not found")
    sys.exit(1)

print("\n" + "="*60)
print(f"User Data for Telegram ID: {telegram_id}")
print("="*60)
print(f"Username: {user.get('username', 'N/A')}")
print(f"First Name: {user.get('first_name', 'N/A')}")
print(f"Subscription Active: {user.get('subscription_active', False)}")
print(f"Stripe Customer ID: {user.get('stripe_customer_id', 'NULL')}")
print(f"Stripe Subscription ID: {user.get('stripe_subscription_id', 'NULL')}")
print(f"Subscription Expires: {user.get('subscription_expires', 'NULL')}")
print("="*60 + "\n")

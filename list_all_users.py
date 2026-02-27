"""List all users in database"""
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase

load_dotenv()
db = BotDatabase()

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
    print("No users found in database")
else:
    print("\n" + "="*80)
    print(f"Total Users: {len(users)}")
    print("="*80)
    print(f"{'Telegram ID':<15} {'Username':<20} {'Active':<10} {'Customer ID':<30}")
    print("-"*80)

    for user in users:
        telegram_id = str(user['telegram_id'])
        username = (user['username'] or 'N/A')[:18]
        active = 'Yes' if user['subscription_active'] else 'No'
        customer_id = (user['stripe_customer_id'] or 'NULL')[:28]

        print(f"{telegram_id:<15} {username:<20} {active:<10} {customer_id:<30}")

    print("="*80 + "\n")

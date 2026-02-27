"""
Create promo codes for the Telegram bot
Run this once to add promo codes to your database
"""

from bot_database import BotDatabase

db = BotDatabase()

# Create a 1-day FREE trial promo code
db.create_promo_code(
    code='FREETRIAL',
    discount_percent=100,  # 100% off = free
    max_uses=1000,         # 1000 people can use it
    days_valid=365         # Code valid for 1 year
)

print("✅ Created FREETRIAL promo code (1-day free)")

# Create other promo codes
db.create_promo_code(
    code='LAUNCH50',
    discount_percent=50,   # 50% off
    max_uses=100,
    days_valid=30
)

print("✅ Created LAUNCH50 promo code (50% off for 30 days)")

db.create_promo_code(
    code='WEEK50',
    discount_percent=50,   # 50% off for a week
    max_uses=200,
    days_valid=7
)

print("✅ Created WEEK50 promo code (50% off for 7 days)")

print("\n🎉 All promo codes created!")
print("\nUsers can now enter these codes during signup.")

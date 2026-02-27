"""
Create promo codes in PostgreSQL database
"""
from bot_database_postgres import BotDatabase
from dotenv import load_dotenv

load_dotenv()

db = BotDatabase()

print("=" * 60)
print("PROMO CODE CREATOR")
print("=" * 60)
print()

# Create FREETRIAL promo code (100% discount)
print("Creating FREETRIAL promo code...")
success = db.create_promo_code(
    code="FREETRIAL",
    discount_percent=100,
    max_uses=100,
    days_valid=365  # Valid for 1 year
)

if success:
    print("[OK] FREETRIAL promo code created successfully!")
    print("    - Discount: 100% (FREE)")
    print("    - Max uses: 100")
    print("    - Valid for: 365 days")
else:
    print("[FAIL] Failed to create FREETRIAL promo code")

print()

# Create additional promo codes (optional)
print("Creating additional promo codes...")

# 50% discount code
success = db.create_promo_code(
    code="SAVE50",
    discount_percent=50,
    max_uses=50,
    days_valid=30
)
if success:
    print("[OK] SAVE50 promo code created (50% off, 50 uses, 30 days)")

# 25% discount code
success = db.create_promo_code(
    code="WELCOME25",
    discount_percent=25,
    max_uses=200,
    days_valid=90
)
if success:
    print("[OK] WELCOME25 promo code created (25% off, 200 uses, 90 days)")

print()
print("=" * 60)
print("Verifying promo codes...")
print("=" * 60)

# Test the promo codes
conn = db.get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT code, discount_percent, max_uses, current_uses,
           active, expires_at
    FROM promo_codes
    ORDER BY discount_percent DESC
""")

codes = cursor.fetchall()

print()
for code in codes:
    print(f"Code: {code['code']}")
    print(f"  Discount: {code['discount_percent']}%")
    print(f"  Uses: {code['current_uses']}/{code['max_uses']}")
    print(f"  Active: {code['active']}")
    print(f"  Expires: {code['expires_at']}")
    print()

db.return_connection(conn)
db.close()

print("=" * 60)
print("[SUCCESS] Promo codes ready to use!")
print("=" * 60)

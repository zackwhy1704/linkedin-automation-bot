"""
Test promo code validation
"""
from bot_database_postgres import BotDatabase
from dotenv import load_dotenv

load_dotenv()

db = BotDatabase()

print("=" * 60)
print("PROMO CODE VALIDATION TEST")
print("=" * 60)
print()

# Test FREETRIAL code
print("Testing FREETRIAL code...")
result = db.validate_promo_code("FREETRIAL")

if result:
    print("[OK] FREETRIAL is VALID!")
    print(f"    Code: {result['code']}")
    print(f"    Discount: {result['discount_percent']}%")
    print(f"    Uses remaining: {result['max_uses'] - result['current_uses']}/{result['max_uses']}")
    print(f"    Expires: {result['expires_at']}")
    print()

    if result['discount_percent'] == 100:
        print("    -> This will give users a FREE TRIAL!")
else:
    print("[FAIL] FREETRIAL code is INVALID or EXPIRED")

print()

# Test other codes
for code in ["SAVE50", "WELCOME25", "INVALID123"]:
    print(f"Testing {code}...")
    result = db.validate_promo_code(code)

    if result:
        print(f"    [OK] {code} is valid - {result['discount_percent']}% off")
    else:
        print(f"    [FAIL] {code} is invalid or expired")

print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)

db.close()

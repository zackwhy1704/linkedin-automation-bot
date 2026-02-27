"""
Check if LinkedIn credentials are stored correctly
"""
from bot_database_postgres import BotDatabase
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import os

load_dotenv()

print("=" * 60)
print("LINKEDIN CREDENTIALS CHECK")
print("=" * 60)
print()

# Get your telegram ID
telegram_id = input("Enter your Telegram ID: ").strip()

if not telegram_id.isdigit():
    print("[ERROR] Telegram ID must be numeric!")
    exit(1)

telegram_id = int(telegram_id)

db = BotDatabase()
cipher = Fernet(os.getenv('ENCRYPTION_KEY').encode())

print(f"Checking credentials for Telegram ID: {telegram_id}")
print()

# Get credentials
creds = db.get_linkedin_credentials(telegram_id)

if not creds:
    print("[FAIL] No credentials found!")
    print()
    print("This means you haven't completed onboarding yet.")
    print("Run the bot and complete the /start flow to save credentials.")
else:
    print("[OK] Credentials found!")
    print()
    print(f"Email: {creds['email']}")

    # Try to decrypt password
    try:
        encrypted_password = creds['encrypted_password']
        decrypted_password = cipher.decrypt(encrypted_password).decode()

        print(f"Encrypted password: {encrypted_password[:20]}... (truncated)")
        print(f"Decrypted password: {'*' * len(decrypted_password)} ({len(decrypted_password)} characters)")
        print()
        print("[OK] Password encryption/decryption working!")
        print()
        print("Your credentials are stored correctly.")
    except Exception as e:
        print(f"[FAIL] Error decrypting password: {e}")
        print()
        print("This could mean:")
        print("1. Encryption key changed")
        print("2. Data corrupted")
        print("3. Wrong format in database")

print()
print("=" * 60)

db.close()

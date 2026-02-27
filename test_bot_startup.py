"""
Test if the Telegram bot can start up properly
"""
import sys
import asyncio
from dotenv import load_dotenv

print("Testing bot startup...")

# Load environment variables
load_dotenv()

try:
    from telegram_bot import main
    from telegram import Update
    from telegram.ext import Application
    import os

    # Verify token exists
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("[FAIL] TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    print(f"[OK] Bot token found: {token[:10]}...")

    # Try to create the application
    try:
        application = Application.builder().token(token).build()
        print("[OK] Application builder works")

        # Test that we can access bot info
        async def test_bot():
            try:
                bot_info = await application.bot.get_me()
                print(f"[OK] Bot connected: @{bot_info.username}")
                print(f"[OK] Bot name: {bot_info.first_name}")
                print(f"[OK] Bot ID: {bot_info.id}")
                return True
            except Exception as e:
                print(f"[FAIL] Cannot connect to bot: {e}")
                return False

        # Run the async test
        result = asyncio.run(test_bot())

        if result:
            print("\n" + "="*60)
            print("BOT STARTUP TEST: SUCCESS")
            print("="*60)
            print("\nThe bot is ready to start!")
            print("Run: python telegram_bot.py")
        else:
            print("\n" + "="*60)
            print("BOT STARTUP TEST: FAILED")
            print("="*60)

    except Exception as e:
        print(f"[FAIL] Application error: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"[FAIL] Import error: {e}")
    import traceback
    traceback.print_exc()

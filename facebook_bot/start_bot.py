"""
Facebook Bot Startup Script
Starts all components: webhook server + Telegram alert worker
"""
import os
import sys
import asyncio
import logging
from threading import Thread
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('facebook_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


def start_webhook_server():
    """Start FastAPI webhook server"""
    import uvicorn
    from facebook_bot.app import app

    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting FastAPI webhook server on port {port}...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


async def start_telegram_worker():
    """Start Telegram alert worker"""
    from facebook_bot.telegram_alerts import TelegramAlerts

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    agent_chat_id = os.getenv("AGENT_TELEGRAM_ID")

    if not bot_token or not agent_chat_id:
        logger.warning("Telegram credentials not set - alerts disabled")
        logger.warning("Set TELEGRAM_BOT_TOKEN and AGENT_TELEGRAM_ID in .env to enable")
        return

    logger.info("Starting Telegram alert worker...")
    alerts = TelegramAlerts(bot_token, agent_chat_id)

    # Send startup notification
    alerts.send_message(
        "🤖 <b>Facebook Bot Started</b>\n\n"
        "Bot is now online and ready to receive leads!"
    )

    # Start worker loop
    await alerts.start_alert_worker(interval=30)


def run_telegram_worker_thread():
    """Run Telegram worker in background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_telegram_worker())


def verify_environment():
    """Check required environment variables"""
    required = [
        'FACEBOOK_PAGE_ACCESS_TOKEN',
        'FACEBOOK_VERIFY_TOKEN',
        'FACEBOOK_PAGE_ID',
        'DATABASE_URL'
    ]

    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please update your .env file")
        sys.exit(1)

    logger.info("✅ Environment variables verified")


def test_database():
    """Test database connection"""
    try:
        from facebook_bot.db_handler import FacebookBotDB
        db = FacebookBotDB()

        # Test query
        result = db.db.execute_query("SELECT 1 as test", fetch='one')
        if result and result.get('test') == 1:
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Database connection test failed")
            return False

    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False


def main():
    """Main startup function"""
    logger.info("=" * 60)
    logger.info("FACEBOOK MESSENGER BOT - STARTUP")
    logger.info("=" * 60)

    # Verify environment
    logger.info("Step 1: Verifying environment variables...")
    verify_environment()

    # Test database
    logger.info("Step 2: Testing database connection...")
    if not test_database():
        logger.error("Database test failed. Please check DATABASE_URL")
        sys.exit(1)

    # Start Telegram worker in background
    logger.info("Step 3: Starting Telegram alert worker...")
    telegram_thread = Thread(target=run_telegram_worker_thread, daemon=True)
    telegram_thread.start()

    # Start webhook server (blocking)
    logger.info("Step 4: Starting webhook server...")
    logger.info("=" * 60)
    logger.info("✅ BOT IS READY!")
    logger.info("=" * 60)
    logger.info(f"Webhook: http://0.0.0.0:{os.getenv('PORT', 8000)}/webhook")
    logger.info("Telegram alerts: Running in background")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    try:
        start_webhook_server()
    except KeyboardInterrupt:
        logger.info("\n\nShutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Telegram Bot Commands Test Suite
Tests all bot commands and identifies issues
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application
import logging

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBotTester:
    """Comprehensive test suite for Telegram bot"""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.test_user_id = os.getenv('TEST_USER_ID')  # Your Telegram ID for testing
        self.results = {}

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

    async def test_bot_connection(self):
        """Test if bot can connect to Telegram"""
        try:
            bot = Bot(token=self.bot_token)
            bot_info = await bot.get_me()
            logger.info(f"✅ Bot connected: @{bot_info.username}")
            self.results['bot_connection'] = {
                'status': 'PASS',
                'bot_username': bot_info.username,
                'bot_id': bot_info.id
            }
            return True
        except Exception as e:
            logger.error(f"❌ Bot connection failed: {e}")
            self.results['bot_connection'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False

    async def test_webapp_server(self):
        """Test if WebApp server is accessible"""
        import aiohttp

        webapp_url = os.getenv('WEBAPP_URL', 'http://localhost:8080')

        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{webapp_url}/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ WebApp server accessible at {webapp_url}")
                        self.results['webapp_server'] = {
                            'status': 'PASS',
                            'url': webapp_url
                        }
                        return True
                    else:
                        raise Exception(f"Server returned status {resp.status}")

        except asyncio.TimeoutError:
            logger.warning(f"⚠️  WebApp server timeout at {webapp_url}")
            logger.info(f"    Start the server with: python webapp_server.py")
            self.results['webapp_server'] = {
                'status': 'FAIL',
                'error': 'Timeout - server not running',
                'solution': 'Run: python webapp_server.py'
            }
            return False
        except Exception as e:
            logger.warning(f"⚠️  WebApp server not accessible: {e}")
            logger.info(f"    Start the server with: python webapp_server.py")
            self.results['webapp_server'] = {
                'status': 'FAIL',
                'error': str(e),
                'solution': 'Run: python webapp_server.py'
            }
            return False

    async def test_database_connection(self):
        """Test database connectivity"""
        try:
            from bot_database_postgres import BotDatabase
            db = BotDatabase()

            # Try a simple query
            result = db.execute_query("SELECT 1 as test", fetch='one')

            if result:
                logger.info("✅ Database connection successful")
                self.results['database'] = {'status': 'PASS'}
                return True
            else:
                raise Exception("Query returned no result")

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.results['database'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False

    async def test_redis_connection(self):
        """Test Redis connectivity (for Celery)"""
        try:
            import redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

            r = redis.from_url(redis_url, decode_responses=True)
            r.ping()

            logger.info("✅ Redis connection successful")
            self.results['redis'] = {'status': 'PASS', 'url': redis_url}
            return True

        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.info(f"    This is OK for single-user mode")
            logger.info(f"    For multi-user: Install Redis and run redis-server")
            self.results['redis'] = {
                'status': 'WARN',
                'error': str(e),
                'note': 'Optional for multi-user mode'
            }
            return False

    async def test_ai_service(self):
        """Test AI service (Anthropic API)"""
        try:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')

            if not anthropic_key or anthropic_key.startswith('sk-ant-xxx'):
                raise ValueError("ANTHROPIC_API_KEY not configured")

            # Try to initialize AI service
            from ai.ai_service import AIService
            ai_service = AIService()

            logger.info("✅ AI service initialized (Anthropic API)")
            self.results['ai_service'] = {'status': 'PASS'}
            return True

        except Exception as e:
            logger.warning(f"⚠️  AI service initialization failed: {e}")
            logger.info(f"    Bot will work but AI features disabled")
            self.results['ai_service'] = {
                'status': 'WARN',
                'error': str(e),
                'note': 'AI features will be disabled'
            }
            return False

    async def test_stripe_integration(self):
        """Test Stripe configuration"""
        try:
            stripe_key = os.getenv('STRIPE_SECRET_KEY')
            stripe_price = os.getenv('STRIPE_PRICE_ID')

            if not stripe_key or stripe_key.startswith('sk_test_51xxx'):
                raise ValueError("STRIPE_SECRET_KEY not configured")

            if not stripe_price or stripe_price.startswith('price_1xxx'):
                raise ValueError("STRIPE_PRICE_ID not configured")

            import stripe
            stripe.api_key = stripe_key

            # Test API connectivity
            stripe.Price.retrieve(stripe_price)

            logger.info("✅ Stripe integration configured")
            self.results['stripe'] = {'status': 'PASS'}
            return True

        except Exception as e:
            logger.warning(f"⚠️  Stripe integration issue: {e}")
            logger.info(f"    Subscriptions will not work")
            self.results['stripe'] = {
                'status': 'WARN',
                'error': str(e),
                'note': 'Required for payment processing'
            }
            return False

    def test_environment_variables(self):
        """Test all required environment variables"""
        required_vars = {
            'TELEGRAM_BOT_TOKEN': 'Critical',
            'ENCRYPTION_KEY': 'Critical',
            'DATABASE_URL': 'Critical',
            'ANTHROPIC_API_KEY': 'Important',
            'STRIPE_SECRET_KEY': 'Important',
            'STRIPE_PRICE_ID': 'Important',
            'REDIS_URL': 'Optional',
            'WEBAPP_URL': 'Optional',
        }

        missing_critical = []
        missing_important = []
        configured = []

        for var, importance in required_vars.items():
            value = os.getenv(var)

            if not value or value.startswith('your_') or value.startswith('sk-ant-xxx'):
                if importance == 'Critical':
                    missing_critical.append(var)
                elif importance == 'Important':
                    missing_important.append(var)
            else:
                configured.append(var)

        logger.info(f"✅ Configured variables: {', '.join(configured)}")

        if missing_critical:
            logger.error(f"❌ Missing CRITICAL variables: {', '.join(missing_critical)}")
            self.results['env_vars'] = {
                'status': 'FAIL',
                'missing_critical': missing_critical
            }
            return False

        if missing_important:
            logger.warning(f"⚠️  Missing IMPORTANT variables: {', '.join(missing_important)}")
            self.results['env_vars'] = {
                'status': 'WARN',
                'missing_important': missing_important
            }

        return True

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "="*60)
        logger.info("LINKEDIN TELEGRAM BOT - COMPREHENSIVE TEST SUITE")
        logger.info("="*60 + "\n")

        tests = [
            ("Environment Variables", self.test_environment_variables),
            ("Bot Connection", self.test_bot_connection),
            ("Database Connection", self.test_database_connection),
            ("Redis Connection (Multi-User)", self.test_redis_connection),
            ("WebApp Server", self.test_webapp_server),
            ("AI Service (Anthropic)", self.test_ai_service),
            ("Stripe Integration", self.test_stripe_integration),
        ]

        for test_name, test_func in tests:
            logger.info(f"\n▶ Testing: {test_name}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
            except Exception as e:
                logger.error(f"  Test crashed: {e}")
                self.results[test_name] = {'status': 'CRASH', 'error': str(e)}

        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)

        pass_count = sum(1 for r in self.results.values() if r.get('status') == 'PASS')
        fail_count = sum(1 for r in self.results.values() if r.get('status') == 'FAIL')
        warn_count = sum(1 for r in self.results.values() if r.get('status') == 'WARN')

        logger.info(f"\n✅ Passed: {pass_count}")
        logger.info(f"❌ Failed: {fail_count}")
        logger.info(f"⚠️  Warnings: {warn_count}")

        # Print failures with solutions
        if fail_count > 0:
            logger.info("\n" + "-"*60)
            logger.info("FAILURES - ACTION REQUIRED:")
            logger.info("-"*60)

            for test_name, result in self.results.items():
                if result.get('status') == 'FAIL':
                    logger.error(f"\n❌ {test_name}")
                    logger.error(f"   Error: {result.get('error', 'Unknown')}")
                    if 'solution' in result:
                        logger.info(f"   Solution: {result['solution']}")

        # Print warnings
        if warn_count > 0:
            logger.info("\n" + "-"*60)
            logger.info("WARNINGS - OPTIONAL FEATURES:")
            logger.info("-"*60)

            for test_name, result in self.results.items():
                if result.get('status') == 'WARN':
                    logger.warning(f"\n⚠️  {test_name}")
                    logger.warning(f"   {result.get('note', result.get('error'))}")

        logger.info("\n" + "="*60)
        logger.info("BOT COMMAND TEST GUIDE")
        logger.info("="*60)
        logger.info("""
To test bot commands manually:

1. Start the bot: python telegram_bot.py

2. In Telegram, send these commands:
   /start - Start onboarding
   /help - List all commands
   /post - Generate and post content
   /engage - Engage with feed
   /autopilot - Run full automation
   /stats - View statistics
   /settings - Update profile
   /schedule - Schedule content
   /connect - Send connection requests
   /jobsearch - Job search features
   /cancelsubscription - Cancel subscription

3. For mobile WebApp testing:
   - Ensure webapp_server.py is running
   - For mobile access, use ngrok: ngrok http 8080
   - Update WEBAPP_URL in .env to the ngrok URL
   - Test /post command on mobile device
        """)

        logger.info("="*60 + "\n")


async def main():
    """Main test runner"""
    tester = TelegramBotTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nTest suite crashed: {e}")
        import traceback
        traceback.print_exc()

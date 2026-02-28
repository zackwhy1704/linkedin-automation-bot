"""
Comprehensive error handling and negative scenario tests for LinkedIn Growth Telegram Bot.
Tests: database failures, missing credentials, Celery dispatch errors,
subscription gating, sign-in failures, and all command handlers.

Run:  python -m pytest tests/test_error_handling.py -v
"""

import os
import sys
import json
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required env vars before importing
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'test_token_123:ABC')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_fake')
os.environ.setdefault('STRIPE_PRICE_ID', 'price_test_fake')
os.environ.setdefault('ENCRYPTION_KEY', 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleT0=')
os.environ.setdefault('DATABASE_HOST', 'localhost')
os.environ.setdefault('DATABASE_PASSWORD', 'test')
os.environ.setdefault('PAYMENT_SERVER_URL', 'http://localhost:5000')

from cryptography.fernet import Fernet
TEST_FERNET_KEY = Fernet.generate_key()
os.environ['ENCRYPTION_KEY'] = TEST_FERNET_KEY.decode()

# Mock psycopg2 pool to prevent real DB connections at import time
import psycopg2.pool as _pool
_orig_pool = _pool.ThreadedConnectionPool
_pool.ThreadedConnectionPool = MagicMock()

# Mock Celery app and browser_pool modules
sys.modules.setdefault('celery_app', MagicMock())
sys.modules.setdefault('browser_pool', MagicMock())

# Now pre-import the bot module with mocked DB
import bot_database_postgres
from multiuser import telegram_bot_multiuser as _bot_mod

# Restore pool (not needed for tests but clean)
_pool.ThreadedConnectionPool = _orig_pool


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def make_update(text=None, user_id=12345, first_name="TestUser", username="testuser",
                callback_data=None, args=None):
    """Create a mock Telegram Update."""
    update = AsyncMock()
    user = MagicMock()
    user.id = user_id
    user.first_name = first_name
    user.username = username
    update.effective_user = user

    if callback_data:
        query = AsyncMock()
        query.data = callback_data
        query.from_user = user
        query.message = AsyncMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update.callback_query = query
        update.message = None
    else:
        update.callback_query = None
        msg = AsyncMock()
        msg.text = text
        msg.delete = AsyncMock()
        msg.reply_text = AsyncMock()
        update.message = msg

    return update


def make_context(user_data=None, args=None, bot_username="TestBot"):
    """Create a mock Telegram context."""
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    context.args = args or []
    context.bot = AsyncMock()
    context.bot.username = bot_username
    context.bot.send_message = AsyncMock()
    return context


def run(coro):
    """Helper to run async functions in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Database failure handling in start()
# ═══════════════════════════════════════════════════════════════════════════

class TestStartDatabaseErrors(unittest.TestCase):
    """Test that start() handles database failures gracefully."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_db_get_user_fails(self, mock_db):
        """start() should show error message if db.get_user() raises exception."""
        mock_db.get_user.side_effect = Exception("Connection refused")

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=[])

        result = run(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary issue", call_args)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_db_get_user_returns_none(self, mock_db):
        """start() with no existing user should start onboarding."""
        mock_db.get_user.return_value = None

        from multiuser.telegram_bot_multiuser import start, PROFILE_INDUSTRY
        update = make_update(text="/start")
        context = make_context(args=[])

        result = run(start(update, context))
        self.assertEqual(result, PROFILE_INDUSTRY)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_existing_inactive_user_starts_onboarding(self, mock_db):
        """start() with existing but inactive user should start onboarding."""
        mock_db.get_user.return_value = {'subscription_active': False}

        from multiuser.telegram_bot_multiuser import start, PROFILE_INDUSTRY
        update = make_update(text="/start")
        context = make_context(args=[])

        result = run(start(update, context))
        self.assertEqual(result, PROFILE_INDUSTRY)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: LinkedIn credential save failures
# ═══════════════════════════════════════════════════════════════════════════

class TestLinkedInPasswordErrors(unittest.TestCase):
    """Test error handling when saving LinkedIn credentials fails."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_linkedin_password_db_save_fails(self, mock_db):
        """If db.save_linkedin_credentials() fails, user should be told to retry."""
        mock_db.save_linkedin_credentials.side_effect = Exception("DB write error")

        from multiuser.telegram_bot_multiuser import linkedin_password, LINKEDIN_PASSWORD
        update = make_update(text="my_password_123")
        context = make_context(user_data={'linkedin_email': 'test@example.com'})

        result = run(linkedin_password(update, context))
        self.assertEqual(result, LINKEDIN_PASSWORD)
        context.bot.send_message.assert_called_once()
        call_args = context.bot.send_message.call_args
        self.assertIn("Failed to save", call_args[1]['text'])

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_linkedin_password_success(self, mock_db):
        """Successful password save should proceed to CONTENT_THEMES."""
        mock_db.save_linkedin_credentials.return_value = None

        from multiuser.telegram_bot_multiuser import linkedin_password, CONTENT_THEMES
        update = make_update(text="my_password_123")
        context = make_context(user_data={'linkedin_email': 'test@example.com'})

        result = run(linkedin_password(update, context))
        self.assertEqual(result, CONTENT_THEMES)
        mock_db.save_linkedin_credentials.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Profile save failures
# ═══════════════════════════════════════════════════════════════════════════

class TestContentGoalsErrors(unittest.TestCase):
    """Test error handling when saving user profile fails."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_content_goals_db_save_fails(self, mock_db):
        """If db.save_user_profile() fails, user should be informed."""
        mock_db.save_user_profile.side_effect = Exception("DB write error")

        from multiuser.telegram_bot_multiuser import content_goals
        from telegram.ext import ConversationHandler
        update = make_update(text="thought leadership, networking")
        context = make_context(user_data={
            'industry': ['tech'],
            'skills': ['Python'],
            'career_goals': ['lead'],
            'tone': ['professional'],
            'content_themes': ['AI'],
            'optimal_times': ['09:00'],
        })

        result = run(content_goals(update, context))
        self.assertEqual(result, ConversationHandler.END)
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Failed to save", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Stats command error handling
# ═══════════════════════════════════════════════════════════════════════════

class TestStatsCommandErrors(unittest.TestCase):
    """Test /stats command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_subscription_check_fails(self, mock_db):
        """If is_subscription_active() raises, show error."""
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats")
        context = make_context()

        # stats_command should not raise
        run(stats_command(update, context))

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_db_get_fails(self, mock_db):
        """If db.get_user_stats() fails, user should see error message."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_stats.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats")
        context = make_context()

        run(stats_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary error", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_returns_none(self, mock_db):
        """If db.get_user_stats() returns None, user should see friendly message."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_stats.return_value = None

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats")
        context = make_context()

        run(stats_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("No statistics", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_success(self, mock_db):
        """Successful stats command should show data."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_stats.return_value = {
            'posts_created': 5,
            'likes_given': 20,
            'comments_made': 10,
            'connections_sent': 3,
            'last_active': 'Today'
        }

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats")
        context = make_context()

        run(stats_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Posts created: 5", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Autopilot command - subscription & credential checks
# ═══════════════════════════════════════════════════════════════════════════

class TestAutopilotCommandErrors(unittest.TestCase):
    """Test /autopilot command error handling and validation."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_no_subscription(self, mock_db):
        """Autopilot without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("active subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_subscription_check_fails(self, mock_db):
        """If subscription check fails, show error."""
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("verify your subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_no_credentials(self, mock_db):
        """Autopilot without LinkedIn credentials should be blocked."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = None

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("LinkedIn account", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_credential_check_fails(self, mock_db):
        """If credential check fails, show error."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("verify your LinkedIn credentials", call_text)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.autopilot_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_celery_dispatch_fails(self, mock_db, mock_task):
        """If Celery dispatch fails, user should be notified."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = {'email': 'a@b.com', 'encrypted_password': b'enc'}
        mock_task.delay.side_effect = Exception("Redis connection refused")

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        # Should have called reply_text at least twice (initiated message + error)
        calls = update.message.reply_text.call_args_list
        error_found = any("temporarily unavailable" in str(c) for c in calls)
        self.assertTrue(error_found)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.autopilot_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_success(self, mock_db, mock_task):
        """Successful autopilot dispatch should work without errors."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = {'email': 'a@b.com', 'encrypted_password': b'enc'}
        mock_task.delay.return_value = MagicMock()

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot")
        context = make_context()

        run(autopilot_command(update, context))
        mock_task.delay.assert_called_once_with(12345)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Engage command - subscription & credential checks
# ═══════════════════════════════════════════════════════════════════════════

class TestEngageCommandErrors(unittest.TestCase):
    """Test /engage command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_no_subscription(self, mock_db):
        """Engage without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage")
        context = make_context()

        run(engage_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe first", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_subscription_check_fails(self, mock_db):
        """If subscription check fails, show error."""
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage")
        context = make_context()

        run(engage_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("verify your subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_no_credentials(self, mock_db):
        """Engage without LinkedIn credentials should be blocked."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = None

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage")
        context = make_context()

        run(engage_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("LinkedIn account", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_success_shows_options(self, mock_db):
        """Engage with valid subscription and credentials shows mode selection."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = {'email': 'a@b.com', 'encrypted_password': b'enc'}

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage")
        context = make_context()

        run(engage_command(update, context))
        update.message.reply_text.assert_called()
        call_text = str(update.message.reply_text.call_args)
        self.assertIn("Engagement Mode", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Connect command - subscription & credential checks
# ═══════════════════════════════════════════════════════════════════════════

class TestConnectCommandErrors(unittest.TestCase):
    """Test /connect command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_connect_no_subscription(self, mock_db):
        """Connect without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import connect_command
        update = make_update(text="/connect")
        context = make_context()

        run(connect_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe first", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_connect_no_credentials(self, mock_db):
        """Connect without LinkedIn credentials should be blocked."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = None

        from multiuser.telegram_bot_multiuser import connect_command
        update = make_update(text="/connect")
        context = make_context()

        run(connect_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("LinkedIn account", call_text)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.send_connection_requests_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_connect_celery_dispatch_fails(self, mock_db, mock_task):
        """If Celery dispatch fails, user should be notified."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_linkedin_credentials.return_value = {'email': 'a@b.com', 'encrypted_password': b'enc'}
        mock_task.delay.side_effect = Exception("Redis down")

        from multiuser.telegram_bot_multiuser import connect_command
        update = make_update(text="/connect")
        context = make_context()

        run(connect_command(update, context))
        calls = update.message.reply_text.call_args_list
        error_found = any("temporarily unavailable" in str(c) for c in calls)
        self.assertTrue(error_found)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Post command - subscription checks
# ═══════════════════════════════════════════════════════════════════════════

class TestPostCommandErrors(unittest.TestCase):
    """Test /post command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_no_subscription(self, mock_db):
        """Post without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import post_command
        update = make_update(text="/post")
        context = make_context()

        run(post_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe first", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_subscription_check_fails(self, mock_db):
        """If subscription check fails, show error."""
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import post_command
        update = make_update(text="/post")
        context = make_context()

        run(post_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("verify your subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_success_shows_options(self, mock_db):
        """Successful post command should show AI/Manual choice."""
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import post_command
        update = make_update(text="/post")
        context = make_context()

        run(post_command(update, context))
        update.message.reply_text.assert_called()
        call_text = str(update.message.reply_text.call_args)
        self.assertIn("Create a LinkedIn Post", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Schedule command error handling
# ═══════════════════════════════════════════════════════════════════════════

class TestScheduleCommandErrors(unittest.TestCase):
    """Test /schedule command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_schedule_no_subscription(self, mock_db):
        """Schedule without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import schedule_command
        update = make_update(text="/schedule")
        context = make_context()

        run(schedule_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe first", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_schedule_profile_load_fails(self, mock_db):
        """If db.get_user_profile() fails, show error."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_profile.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import schedule_command
        update = make_update(text="/schedule")
        context = make_context()

        run(schedule_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Failed to load", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_schedule_no_profile(self, mock_db):
        """Schedule with no profile should tell user to onboard first."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_profile.return_value = None

        from multiuser.telegram_bot_multiuser import schedule_command
        update = make_update(text="/schedule")
        context = make_context()

        run(schedule_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("No profile found", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Settings command error handling
# ═══════════════════════════════════════════════════════════════════════════

class TestSettingsCommandErrors(unittest.TestCase):
    """Test /settings command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_no_subscription(self, mock_db):
        """Settings without active subscription should be blocked."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings")
        context = make_context()

        run(settings_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe first", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_subscription_check_fails(self, mock_db):
        """If subscription check fails, show error."""
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings")
        context = make_context()

        run(settings_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("verify your subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_profile_load_fails(self, mock_db):
        """If db.get_user_profile() fails, show error."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_profile.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings")
        context = make_context()

        run(settings_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary error", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_no_profile(self, mock_db):
        """Settings with no profile should tell user to onboard."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_profile.return_value = None

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings")
        context = make_context()

        run(settings_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("No profile found", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Promo code validation errors
# ═══════════════════════════════════════════════════════════════════════════

class TestPromoCodeErrors(unittest.TestCase):
    """Test promo code validation error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_db_fails(self, mock_db):
        """If db.validate_promo_code() fails, user should see error."""
        mock_db.validate_promo_code.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING
        update = make_update(text="TESTCODE")
        context = make_context()

        result = run(handle_promo_code_input(update, context))
        self.assertEqual(result, PAYMENT_PROCESSING)
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary error", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_invalid(self, mock_db):
        """Invalid promo code should show invalid message."""
        mock_db.validate_promo_code.return_value = None

        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING
        update = make_update(text="INVALIDCODE")
        context = make_context()

        result = run(handle_promo_code_input(update, context))
        self.assertEqual(result, PAYMENT_PROCESSING)
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Invalid promo code", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_free_success(self, mock_db):
        """Valid FREE promo code should activate subscription."""
        mock_db.validate_promo_code.return_value = {'is_free_bypass': True}
        mock_db.use_promo_code.return_value = None
        mock_db.activate_subscription.return_value = True

        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler
        update = make_update(text="FREE")
        context = make_context()

        result = run(handle_promo_code_input(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.use_promo_code.assert_called_once_with("FREE")
        mock_db.activate_subscription.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Job search config errors
# ═══════════════════════════════════════════════════════════════════════════

class TestJobSearchErrors(unittest.TestCase):
    """Test job search command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_job_search_config_fails(self, mock_db):
        """If db.get_job_search_config() fails, show error."""
        mock_db.get_job_search_config.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import job_search_command
        update = make_update(text="/jobsearch")
        context = make_context()

        run(job_search_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary error", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_job_search_no_config(self, mock_db):
        """No config should prompt user to set up."""
        mock_db.get_job_search_config.return_value = None

        from multiuser.telegram_bot_multiuser import job_search_command
        update = make_update(text="/jobsearch")
        context = make_context()

        run(job_search_command(update, context))
        update.message.reply_text.assert_called()
        call_text = str(update.message.reply_text.call_args)
        self.assertIn("/setjob", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stop_job_db_fails(self, mock_db):
        """If stop job DB call fails, show error."""
        mock_db.execute_query.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import stop_job_command
        update = make_update(text="/stopjob")
        context = make_context()

        run(stop_job_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("temporary error", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Setjob save config errors
# ═══════════════════════════════════════════════════════════════════════════

class TestSetjobErrors(unittest.TestCase):
    """Test /setjob confirm error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_setjob_confirm_db_save_fails(self, mock_db):
        """If db.save_job_search_config() fails, user should be notified."""
        mock_db.save_job_search_config.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import setjob_confirm_callback
        from telegram.ext import ConversationHandler
        update = make_update(callback_data='setjob_confirm')
        context = make_context(user_data={
            'setjob_roles': ['Software Engineer'],
            'setjob_locations': ['Singapore']
        })

        result = run(setjob_confirm_callback(update, context))
        self.assertEqual(result, ConversationHandler.END)
        update.callback_query.edit_message_text.assert_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Failed to save", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_setjob_confirm_success(self, mock_db):
        """Successful setjob confirmation should activate scanning."""
        mock_db.save_job_search_config.return_value = None

        from multiuser.telegram_bot_multiuser import setjob_confirm_callback
        from telegram.ext import ConversationHandler
        update = make_update(callback_data='setjob_confirm')
        context = make_context(user_data={
            'setjob_roles': ['Software Engineer'],
            'setjob_locations': ['Singapore']
        })

        result = run(setjob_confirm_callback(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.save_job_search_config.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment cancel deep link handling
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentCancelDeepLink(unittest.TestCase):
    """Test that payment_cancel deep link shows retry options."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_payment_cancel_shows_retry_buttons(self, mock_db):
        """Payment cancel deep link should show retry and promo code buttons."""
        from multiuser.telegram_bot_multiuser import start, PAYMENT_PROCESSING
        update = make_update(text="/start")
        context = make_context(args=['payment_cancel'])

        result = run(start(update, context))
        self.assertEqual(result, PAYMENT_PROCESSING)
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Payment was not completed", call_text)
        self.assertIn("No charges", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Cancel subscription error paths
# ═══════════════════════════════════════════════════════════════════════════

class TestCancelSubscriptionErrors(unittest.TestCase):
    """Test cancel subscription command error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_sub_no_user_still_shows_dialog(self, mock_db):
        """Even if no user data, cancellation dialog should still show."""
        mock_db.get_user.return_value = None

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription")
        context = make_context()

        run(cancel_subscription_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("cancel your subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_sub_db_error_still_shows_dialog(self, mock_db):
        """Even if DB fails, cancellation dialog should still show."""
        mock_db.get_user.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription")
        context = make_context()

        run(cancel_subscription_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("cancel your subscription", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Handle Engage Callback - Celery dispatch errors
# ═══════════════════════════════════════════════════════════════════════════

class TestEngageCallbackErrors(unittest.TestCase):
    """Test engage callback Celery dispatch error handling."""

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.reply_engagement_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_reply_engagement_celery_fails(self, mock_db, mock_task):
        """If Celery dispatch fails for reply engagement, user is notified."""
        mock_task.delay.side_effect = Exception("Redis down")

        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_replies')
        context = make_context()

        run(handle_engage_callback(update, context))
        # Check error message was sent
        reply_calls = update.callback_query.message.reply_text.call_args_list
        error_found = any("temporarily unavailable" in str(c) for c in reply_calls)
        self.assertTrue(error_found)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.engage_with_feed_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_feed_engagement_celery_fails(self, mock_db, mock_task):
        """If Celery dispatch fails for feed engagement, user is notified."""
        mock_task.delay.side_effect = Exception("Redis down")

        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_feed')
        context = make_context()

        run(handle_engage_callback(update, context))
        reply_calls = update.callback_query.message.reply_text.call_args_list
        error_found = any("temporarily unavailable" in str(c) for c in reply_calls)
        self.assertTrue(error_found)

    def test_engage_cancel(self):
        """Cancel button should just dismiss."""
        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_cancel')
        context = make_context()

        run(handle_engage_callback(update, context))
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("cancelled", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scan job now - Celery dispatch errors
# ═══════════════════════════════════════════════════════════════════════════

class TestScanJobNowErrors(unittest.TestCase):
    """Test scan job now command Celery dispatch error handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_scan_job_no_config(self, mock_db):
        """No job config should prompt setup."""
        mock_db.get_job_search_config.return_value = None

        from multiuser.telegram_bot_multiuser import scan_job_now_command
        update = make_update(text="/scanjobnow")
        context = make_context()

        run(scan_job_now_command(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("/setjob", call_text)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.scan_jobs_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_scan_job_celery_fails(self, mock_db, mock_task):
        """If Celery dispatch fails, user should be notified."""
        mock_db.get_job_search_config.return_value = {
            'target_roles': ['Software Engineer'],
            'scan_keywords': [],
            'resume_keywords': []
        }
        mock_task.delay.side_effect = Exception("Redis down")

        from multiuser.telegram_bot_multiuser import scan_job_now_command
        update = make_update(text="/scanjobnow")
        context = make_context()

        run(scan_job_now_command(update, context))
        calls = update.message.reply_text.call_args_list
        error_found = any("temporarily unavailable" in str(c) for c in calls)
        self.assertTrue(error_found)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Help command always works
# ═══════════════════════════════════════════════════════════════════════════

class TestHelpCommand(unittest.TestCase):
    """Test /help command works regardless of state."""

    def test_help_always_responds(self):
        """Help command should always return help text."""
        from multiuser.telegram_bot_multiuser import help_command
        update = make_update(text="/help")
        context = make_context()

        run(help_command(update, context))
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("/autopilot", call_text)
        self.assertIn("/post", call_text)
        self.assertIn("/engage", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Post callback - various paths
# ═══════════════════════════════════════════════════════════════════════════

class TestPostCallbackPaths(unittest.TestCase):
    """Test various post callback paths."""

    def test_post_discard(self):
        """Discard should clear post data."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_discard')
        context = make_context(user_data={'generated_post': 'test post', 'awaiting_custom_post': True})

        run(handle_post_callback(update, context))
        update.callback_query.edit_message_text.assert_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("discarded", call_text)
        self.assertNotIn('generated_post', context.user_data)

    def test_post_write_own(self):
        """Write own should set awaiting flag."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_write_own')
        context = make_context()

        run(handle_post_callback(update, context))
        self.assertTrue(context.user_data.get('awaiting_custom_post'))

    def test_post_mobile_no_content(self):
        """Mobile post with no content should show error."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_mobile')
        context = make_context(user_data={})

        run(handle_post_callback(update, context))
        update.callback_query.edit_message_text.assert_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("not found", call_text)

    def test_post_approve_no_content(self):
        """Browser post approval with no content should show error."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_approve_12345')
        context = make_context(user_data={})

        run(handle_post_callback(update, context))
        update.callback_query.edit_message_text.assert_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("not found", call_text)

    def test_post_confirmed_logs_action(self):
        """Post confirmation should attempt to log action."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_confirmed')
        context = make_context()

        run(handle_post_callback(update, context))
        update.callback_query.edit_message_text.assert_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Confirmed", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Custom post text handling
# ═══════════════════════════════════════════════════════════════════════════

class TestCustomPostText(unittest.TestCase):
    """Test custom post text input handling."""

    def test_custom_post_empty(self):
        """Empty custom post should show error."""
        from multiuser.telegram_bot_multiuser import handle_custom_post_text
        update = make_update(text="")
        context = make_context(user_data={'awaiting_custom_post': True})

        run(handle_custom_post_text(update, context))
        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("cannot be empty", call_text)

    def test_custom_post_not_awaiting(self):
        """If not awaiting custom post, should be ignored."""
        from multiuser.telegram_bot_multiuser import handle_custom_post_text
        update = make_update(text="My test post")
        context = make_context(user_data={})

        run(handle_custom_post_text(update, context))
        update.message.reply_text.assert_not_called()


if __name__ == '__main__':
    unittest.main()

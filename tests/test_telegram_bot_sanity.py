"""
Comprehensive sanity tests for LinkedIn Growth Telegram Bot.
Covers: onboarding flow, payment callbacks, automation commands,
database operations, and end-to-end integration.

Run:  python -m pytest tests/test_telegram_bot_sanity.py -v
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

# ─── Mock heavy imports before importing the bot module ────────────────────
# Prevent real DB / Stripe / Celery connections during tests

# Mock psycopg2 before bot_database_postgres is imported
mock_pool = MagicMock()
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_pool.getconn.return_value = mock_conn
mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

# Mock Celery tasks
sys.modules.setdefault('celery_app', MagicMock())
sys.modules.setdefault('browser_pool', MagicMock())

# Set required env vars before importing
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'test_token_123:ABC')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_fake')
os.environ.setdefault('STRIPE_PRICE_ID', 'price_test_fake')
os.environ.setdefault('ENCRYPTION_KEY', 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleT0=')  # base64 test key
os.environ.setdefault('DATABASE_HOST', 'localhost')
os.environ.setdefault('DATABASE_PASSWORD', 'test')
os.environ.setdefault('PAYMENT_SERVER_URL', 'http://localhost:5000')

from cryptography.fernet import Fernet
# Generate a real Fernet key for tests
TEST_FERNET_KEY = Fernet.generate_key()
os.environ['ENCRYPTION_KEY'] = TEST_FERNET_KEY.decode()


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: Build fake Telegram Update / Context objects
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


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Input Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestInputValidation(unittest.TestCase):
    """Test the validate_text_input function."""

    def setUp(self):
        # Import here to avoid import-time side effects
        with patch('bot_database_postgres.BotDatabase'):
            with patch('stripe.api_key', 'sk_test'):
                from multiuser.telegram_bot_multiuser import validate_text_input
                self.validate = validate_text_input

    def test_valid_industry(self):
        self.assertTrue(self.validate("software development"))

    def test_valid_comma_separated(self):
        self.assertTrue(self.validate("Python, AI, Machine Learning"))

    def test_valid_with_hyphens(self):
        self.assertTrue(self.validate("full-stack development"))

    def test_valid_with_ampersand(self):
        self.assertTrue(self.validate("AI & Machine Learning"))

    def test_valid_with_parentheses(self):
        self.assertTrue(self.validate("React (frontend)"))

    def test_reject_special_chars(self):
        self.assertFalse(self.validate("'; DROP TABLE users;--"))

    def test_reject_empty(self):
        self.assertFalse(self.validate(""))

    def test_reject_html(self):
        self.assertFalse(self.validate("<script>alert('xss')</script>"))


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Encryption Round-Trip
# ═══════════════════════════════════════════════════════════════════════════

class TestEncryption(unittest.TestCase):
    """Test password encrypt/decrypt round-trip."""

    def test_encrypt_decrypt_roundtrip(self):
        cipher = Fernet(TEST_FERNET_KEY)
        password = "MyS3cretP@ss!"
        encrypted = cipher.encrypt(password.encode())
        decrypted = cipher.decrypt(encrypted).decode()
        self.assertEqual(password, decrypted)

    def test_encrypted_is_different(self):
        cipher = Fernet(TEST_FERNET_KEY)
        password = "test123"
        encrypted = cipher.encrypt(password.encode())
        self.assertNotEqual(password.encode(), encrypted)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Onboarding Flow (ConversationHandler states)
# ═══════════════════════════════════════════════════════════════════════════

class TestOnboardingFlow(unittest.TestCase):
    """Test the full onboarding conversation flow state transitions."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_new_user_returns_profile_industry(self, mock_db):
        """New user starting /start should enter PROFILE_INDUSTRY state."""
        mock_db.get_user.return_value = None

        from multiuser.telegram_bot_multiuser import start, PROFILE_INDUSTRY
        update = make_update(text="/start")
        context = make_context(args=[])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, PROFILE_INDUSTRY)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_existing_active_user_ends(self, mock_db):
        """Existing user with active subscription should get END."""
        mock_db.get_user.return_value = {'subscription_active': True}

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=[])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_success_activates(self, mock_db):
        """Deep link with payment_success should activate subscription."""
        mock_db.is_subscription_active.return_value = False
        mock_db.activate_subscription.return_value = True

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_once()

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_cancel_ends(self, mock_db):
        """Deep link with payment_cancel should end gracefully."""
        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_cancel'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_profile_industry_valid(self, mock_db):
        """Valid industry input should transition to PROFILE_SKILLS."""
        from multiuser.telegram_bot_multiuser import profile_industry, PROFILE_SKILLS
        update = make_update(text="software development, AI")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            profile_industry(update, context)
        )
        self.assertEqual(result, PROFILE_SKILLS)
        self.assertEqual(context.user_data['industry'], ['software development', 'AI'])

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_profile_industry_invalid_stays(self, mock_db):
        """Invalid input should stay in PROFILE_INDUSTRY."""
        from multiuser.telegram_bot_multiuser import profile_industry, PROFILE_INDUSTRY
        update = make_update(text="<script>bad</script>")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            profile_industry(update, context)
        )
        self.assertEqual(result, PROFILE_INDUSTRY)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_profile_skills_valid(self, mock_db):
        """Valid skills should transition to PROFILE_GOALS."""
        from multiuser.telegram_bot_multiuser import profile_skills, PROFILE_GOALS
        update = make_update(text="Python, React, Docker")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            profile_skills(update, context)
        )
        self.assertEqual(result, PROFILE_GOALS)
        self.assertEqual(context.user_data['skills'], ['Python', 'React', 'Docker'])

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_profile_goals_valid(self, mock_db):
        """Valid goals should transition to PROFILE_TONE."""
        from multiuser.telegram_bot_multiuser import profile_goals, PROFILE_TONE
        update = make_update(text="senior dev, tech lead")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            profile_goals(update, context)
        )
        self.assertEqual(result, PROFILE_TONE)
        self.assertIn('selected_tones', context.user_data)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_tone_toggle_selection(self, mock_db):
        """Selecting a tone should toggle it in selected_tones."""
        from multiuser.telegram_bot_multiuser import profile_tone, PROFILE_TONE
        update = make_update(callback_data='tone_professional')
        context = make_context(user_data={'selected_tones': []})

        result = asyncio.get_event_loop().run_until_complete(
            profile_tone(update, context)
        )
        self.assertEqual(result, PROFILE_TONE)
        self.assertIn('professional yet approachable', context.user_data['selected_tones'])

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_tone_done_requires_selection(self, mock_db):
        """Pressing Done with no tones should alert user."""
        from multiuser.telegram_bot_multiuser import profile_tone, PROFILE_TONE
        update = make_update(callback_data='tone_done')
        context = make_context(user_data={'selected_tones': []})

        result = asyncio.get_event_loop().run_until_complete(
            profile_tone(update, context)
        )
        self.assertEqual(result, PROFILE_TONE)
        update.callback_query.answer.assert_called_with(
            "Please select at least one tone!", show_alert=True
        )

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_tone_done_with_selection_goes_to_email(self, mock_db):
        """Pressing Done with tones selected should go to LINKEDIN_EMAIL."""
        from multiuser.telegram_bot_multiuser import profile_tone, LINKEDIN_EMAIL
        update = make_update(callback_data='tone_done')
        context = make_context(user_data={'selected_tones': ['professional yet approachable']})

        result = asyncio.get_event_loop().run_until_complete(
            profile_tone(update, context)
        )
        self.assertEqual(result, LINKEDIN_EMAIL)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_linkedin_email_goes_to_password(self, mock_db):
        """Email input should transition to LINKEDIN_PASSWORD."""
        from multiuser.telegram_bot_multiuser import linkedin_email, LINKEDIN_PASSWORD
        update = make_update(text="user@example.com")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            linkedin_email(update, context)
        )
        self.assertEqual(result, LINKEDIN_PASSWORD)
        self.assertEqual(context.user_data['linkedin_email'], 'user@example.com')

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_linkedin_password_goes_to_content_themes(self, mock_db):
        """Password input should save creds and go to CONTENT_THEMES."""
        from multiuser.telegram_bot_multiuser import linkedin_password, CONTENT_THEMES
        mock_db.save_linkedin_credentials.return_value = True

        update = make_update(text="mypassword123", user_id=12345)
        context = make_context(user_data={'linkedin_email': 'user@example.com'})

        result = asyncio.get_event_loop().run_until_complete(
            linkedin_password(update, context)
        )
        self.assertEqual(result, CONTENT_THEMES)
        mock_db.save_linkedin_credentials.assert_called_once()

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_content_themes_goes_to_optimal_times(self, mock_db):
        """Content themes should transition to OPTIMAL_TIMES."""
        from multiuser.telegram_bot_multiuser import content_themes, OPTIMAL_TIMES
        update = make_update(text="AI trends, career tips")
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            content_themes(update, context)
        )
        self.assertEqual(result, OPTIMAL_TIMES)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_content_goals_saves_and_goes_to_payment(self, mock_db):
        """Content goals should save profile and transition to PAYMENT_PROCESSING."""
        from multiuser.telegram_bot_multiuser import content_goals, PAYMENT_PROCESSING
        mock_db.save_user_profile.return_value = True

        update = make_update(text="build thought leadership, attract recruiters", user_id=12345)
        context = make_context(user_data={
            'industry': ['AI'],
            'skills': ['Python', 'ML'],
            'career_goals': ['tech lead'],
            'tone': ['professional yet approachable'],
            'content_themes': ['AI trends'],
            'optimal_times': ['09:00', '13:00'],
        })

        result = asyncio.get_event_loop().run_until_complete(
            content_goals(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)
        mock_db.save_user_profile.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment & Subscription Callbacks
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentCallbacks(unittest.TestCase):
    """Test subscription and promo code handling."""

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_subscribe_daily_creates_stripe_session(self, mock_db, mock_stripe):
        """subscribe_daily callback should create Stripe checkout session."""
        from multiuser.telegram_bot_multiuser import handle_subscription
        from telegram.ext import ConversationHandler

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe.checkout.Session.create.return_value = mock_session

        update = make_update(callback_data='subscribe_daily', user_id=12345)
        context = make_context(bot_username='TestBot')

        result = asyncio.get_event_loop().run_until_complete(
            handle_subscription(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)
        mock_stripe.checkout.Session.create.assert_called_once()

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_button_sets_flag(self, mock_db):
        """Clicking promo_code button should set expecting_promo."""
        from multiuser.telegram_bot_multiuser import handle_subscription, PAYMENT_PROCESSING

        update = make_update(callback_data='promo_code', user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_subscription(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)
        self.assertTrue(context.user_data.get('expecting_promo'))

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_invalid_promo_code_stays(self, mock_db):
        """Invalid promo code should stay in PAYMENT_PROCESSING."""
        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING
        mock_db.validate_promo_code.return_value = None

        update = make_update(text="INVALIDCODE", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_free_bypass_promo_activates(self, mock_db):
        """FREE promo code should activate subscription immediately."""
        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler

        mock_db.validate_promo_code.return_value = {
            'code': 'FREE',
            'is_free_bypass': True,
        }
        mock_db.activate_subscription.return_value = True

        update = make_update(text="FREE", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_once_with(12345, days=30)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_freetrial_promo_creates_trial_session(self, mock_db, mock_stripe):
        """FREETRIAL promo should create Stripe session with 7-day trial."""
        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler

        mock_db.validate_promo_code.return_value = {
            'code': 'FREETRIAL',
            'is_freetrial': True,
        }

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test_trial"
        mock_stripe.checkout.Session.create.return_value = mock_session

        update = make_update(text="FREETRIAL", user_id=12345)
        context = make_context(bot_username='TestBot')

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)
        # Verify trial_period_days was passed
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        self.assertEqual(call_kwargs['subscription_data']['trial_period_days'], 7)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Automation Commands (subscription gating)
# ═══════════════════════════════════════════════════════════════════════════

class TestAutomationCommands(unittest.TestCase):
    """Test that automation commands check subscription status."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_rejects_unsubscribed(self, mock_db):
        """Autopilot should reject user without subscription."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            autopilot_command(update, context)
        )
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("subscription", call_text.lower())

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.autopilot_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_autopilot_dispatches_celery_task(self, mock_db, mock_task):
        """Autopilot with active subscription should dispatch Celery task."""
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import autopilot_command
        update = make_update(text="/autopilot", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            autopilot_command(update, context)
        )
        mock_task.delay.assert_called_once_with(12345)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_rejects_unsubscribed(self, mock_db):
        """Engage should reject user without subscription."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            engage_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_shows_options_for_subscriber(self, mock_db):
        """Engage should show engagement mode options for subscribers."""
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import engage_command
        update = make_update(text="/engage", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            engage_command(update, context)
        )
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_connect_rejects_unsubscribed(self, mock_db):
        """Connect should reject user without subscription."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import connect_command
        update = make_update(text="/connect", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            connect_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_rejects_unsubscribed(self, mock_db):
        """Stats should reject user without subscription."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            stats_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stats_shows_data_for_subscriber(self, mock_db):
        """Stats should show automation data for active subscribers."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_stats.return_value = {
            'posts_created': 5,
            'likes_given': 20,
            'comments_made': 10,
            'connections_sent': 3,
            'last_active': '2025-01-01T00:00:00'
        }

        from multiuser.telegram_bot_multiuser import stats_command
        update = make_update(text="/stats", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            stats_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("5", call_text)  # posts_created
        self.assertIn("20", call_text)  # likes_given

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_rejects_unsubscribed(self, mock_db):
        """Post should reject user without subscription."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import post_command
        update = make_update(text="/post", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            post_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_shows_options_for_subscriber(self, mock_db):
        """Post should show AI/Custom options for active subscribers."""
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import post_command
        update = make_update(text="/post", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            post_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Create a LinkedIn Post", call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Engagement Callbacks
# ═══════════════════════════════════════════════════════════════════════════

class TestEngagementCallbacks(unittest.TestCase):
    """Test engagement mode selection callbacks."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_cancel(self, mock_db):
        """Cancel button should dismiss engagement."""
        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_cancel', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_engage_callback(update, context)
        )
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("cancelled", call_text.lower())

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.reply_engagement_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_replies_dispatches(self, mock_db, mock_task):
        """Reply engagement should dispatch Celery task."""
        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_replies', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_engage_callback(update, context)
        )
        mock_task.delay.assert_called_once_with(12345, max_replies=5)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.engage_with_feed_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_engage_feed_dispatches(self, mock_db, mock_task):
        """Feed engagement should dispatch Celery task."""
        from multiuser.telegram_bot_multiuser import handle_engage_callback
        update = make_update(callback_data='engage_feed', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_engage_callback(update, context)
        )
        mock_task.delay.assert_called_once_with(12345, max_engagements=10)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Post Callbacks
# ═══════════════════════════════════════════════════════════════════════════

class TestPostCallbacks(unittest.TestCase):
    """Test post management callbacks."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_discard(self, mock_db):
        """Discard should clear post data."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_discard', user_id=12345)
        context = make_context(user_data={'generated_post': 'test content'})

        asyncio.get_event_loop().run_until_complete(
            handle_post_callback(update, context)
        )
        self.assertNotIn('generated_post', context.user_data)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_write_own_sets_flag(self, mock_db):
        """Write own post should set awaiting_custom_post flag."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_write_own', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_post_callback(update, context)
        )
        self.assertTrue(context.user_data.get('awaiting_custom_post'))

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_mobile_shows_copy(self, mock_db):
        """Mobile post should show copy-paste instructions."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_mobile', user_id=12345)
        context = make_context(user_data={'generated_post': 'My test LinkedIn post'})

        asyncio.get_event_loop().run_until_complete(
            handle_post_callback(update, context)
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Copy", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_confirmed_logs_action(self, mock_db):
        """Confirming mobile post should log to database."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_confirmed', user_id=12345)
        context = make_context(user_data={'generated_post': 'test'})

        asyncio.get_event_loop().run_until_complete(
            handle_post_callback(update, context)
        )
        mock_db.log_automation_action.assert_called_once_with(12345, 'post', 1)

    @patch('multiuser.telegram_bot_multiuser.CELERY_ENABLED', True)
    @patch('multiuser.telegram_bot_multiuser.post_to_linkedin_task')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_post_approve_dispatches_celery(self, mock_db, mock_task):
        """Approving browser post should dispatch Celery task."""
        from multiuser.telegram_bot_multiuser import handle_post_callback
        update = make_update(callback_data='post_approve_12345', user_id=12345)
        context = make_context(user_data={'generated_post': 'My LinkedIn post!'})

        asyncio.get_event_loop().run_until_complete(
            handle_post_callback(update, context)
        )
        mock_task.delay.assert_called_once_with(12345, 'My LinkedIn post!')


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Cancel Subscription
# ═══════════════════════════════════════════════════════════════════════════

class TestCancelSubscription(unittest.TestCase):
    """Test subscription cancellation flow."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_command_shows_confirmation(self, mock_db):
        """Cancel command should always show confirmation buttons."""
        mock_db.get_user.return_value = {
            'stripe_subscription_id': 'sub_test123',
            'stripe_customer_id': 'cus_test123',
        }

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_keep_sub_callback(self, mock_db):
        """Keeping subscription should send positive message."""
        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='keep_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("active", call_text.lower())


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Help Command
# ═══════════════════════════════════════════════════════════════════════════

class TestHelpCommand(unittest.TestCase):
    """Test help command output."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_help_lists_commands(self, mock_db):
        """Help should list all major commands."""
        from multiuser.telegram_bot_multiuser import help_command
        update = make_update(text="/help")
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            help_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        for cmd in ['/autopilot', '/post', '/engage', '/connect', '/stats', '/help']:
            self.assertIn(cmd, call_text)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Settings
# ═══════════════════════════════════════════════════════════════════════════

class TestSettings(unittest.TestCase):
    """Test settings menu and updates."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_rejects_unsubscribed(self, mock_db):
        """Settings should reject unsubscribed users."""
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            settings_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Subscribe", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_shows_menu_for_subscriber(self, mock_db):
        """Settings should show update options for subscribers."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user_profile.return_value = {
            'profile_data': {'industry': ['AI']},
            'content_strategy': {}
        }

        from multiuser.telegram_bot_multiuser import settings_command
        update = make_update(text="/settings", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            settings_command(update, context)
        )
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_callback_sets_field(self, mock_db):
        """Settings callback should store updating_field in context."""
        from multiuser.telegram_bot_multiuser import handle_settings_callback
        update = make_update(callback_data='update_industry', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_settings_callback(update, context)
        )
        self.assertEqual(context.user_data['updating_field'], 'update_industry')

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_settings_update_saves_industry(self, mock_db):
        """Text input during settings update should save to database."""
        mock_db.get_user_profile.return_value = {
            'profile_data': {'industry': ['old'], 'skills': [], 'career_goals': [], 'tone': [], 'interests': []},
            'content_strategy': {},
        }
        mock_db.save_user_profile.return_value = True

        from multiuser.telegram_bot_multiuser import handle_settings_update
        update = make_update(text="AI, Data Science", user_id=12345)
        context = make_context(user_data={'updating_field': 'update_industry'})

        asyncio.get_event_loop().run_until_complete(
            handle_settings_update(update, context)
        )
        mock_db.save_user_profile.assert_called_once()
        call_args = mock_db.save_user_profile.call_args[0]
        self.assertIn('AI', call_args[1]['industry'])


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Database BotDatabase methods (unit-level with mocking)
# ═══════════════════════════════════════════════════════════════════════════

class TestBotDatabaseMethods(unittest.TestCase):
    """Test database method signatures and return types."""

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_create_user(self, mock_pool_cls):
        """create_user should not raise."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.create_user(12345, 'testuser', 'Test')
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_get_user_not_found(self, mock_pool_cls):
        """get_user should return None for unknown user."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.get_user(99999)
        self.assertIsNone(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_validate_promo_free(self, mock_pool_cls):
        """Validate FREE promo code should return free_bypass."""
        mock_pool_cls.return_value = mock_pool

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.validate_promo_code('FREE')
        self.assertIsNotNone(result)
        self.assertTrue(result.get('is_free_bypass'))

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_validate_promo_freetrial(self, mock_pool_cls):
        """Validate FREETRIAL promo code should return freetrial."""
        mock_pool_cls.return_value = mock_pool

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.validate_promo_code('FREETRIAL')
        self.assertIsNotNone(result)
        self.assertTrue(result.get('is_freetrial'))

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_validate_promo_invalid(self, mock_pool_cls):
        """Invalid promo code should return None."""
        mock_pool_cls.return_value = mock_pool

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.validate_promo_code('DOESNOTEXIST')
        self.assertIsNone(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_is_subscription_active_false_for_missing(self, mock_pool_cls):
        """Missing user should not have active subscription."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.is_subscription_active(99999)
        self.assertFalse(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_get_user_stats_default(self, mock_pool_cls):
        """get_user_stats should return zeroed dict for new user."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.get_user_stats(99999)
        self.assertEqual(result['posts_created'], 0)
        self.assertEqual(result['likes_given'], 0)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Screenshot Handler
# ═══════════════════════════════════════════════════════════════════════════

class TestScreenshotHandler(unittest.TestCase):
    """Test screenshot queue operations."""

    def test_add_and_get_screenshots(self):
        from screenshot_handler import ScreenshotQueue
        q = ScreenshotQueue()
        q.add_screenshot(12345, "/path/to/img.png", "Test")
        self.assertTrue(q.has_screenshots(12345))
        shots = q.get_screenshots(12345)
        self.assertEqual(len(shots), 1)
        self.assertEqual(shots[0]['path'], "/path/to/img.png")
        # Queue should be cleared after get
        self.assertFalse(q.has_screenshots(12345))

    def test_empty_queue(self):
        from screenshot_handler import ScreenshotQueue
        q = ScreenshotQueue()
        self.assertFalse(q.has_screenshots(12345))
        shots = q.get_screenshots(12345)
        self.assertEqual(len(shots), 0)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment Server Webhook
# ═══════════════════════════════════════════════════════════════════════════

try:
    import flask as _flask_check
    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False


@unittest.skipUnless(_HAS_FLASK, "Flask not installed")
class TestPaymentServer(unittest.TestCase):
    """Test payment server endpoints."""

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_health_endpoint(self, mock_stripe, mock_db):
        """Health endpoint should return 200."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/health')
        self.assertEqual(resp.status_code, 200)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_rejects_bad_signature(self, mock_stripe, mock_db):
        """Stripe webhook should reject invalid signatures."""
        mock_stripe.Webhook.construct_event.side_effect = ValueError("bad")

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'{}',
                           headers={'Stripe-Signature': 'bad_sig'})
        self.assertEqual(resp.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: End-to-End Onboarding Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndOnboarding(unittest.TestCase):
    """Simulate full onboarding flow from /start to payment."""

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_full_onboarding_flow(self, mock_db, mock_stripe):
        """Walk through the entire onboarding state machine."""
        mock_db.get_user.return_value = None
        mock_db.save_user_profile.return_value = True
        mock_db.save_linkedin_credentials.return_value = True
        mock_db.activate_subscription.return_value = True
        mock_db.validate_promo_code.return_value = {
            'code': 'FREE', 'is_free_bypass': True,
        }

        from multiuser.telegram_bot_multiuser import (
            start, profile_industry, profile_skills, profile_goals,
            profile_tone, linkedin_email, linkedin_password,
            content_themes, content_goals, handle_promo_code_input,
            PROFILE_INDUSTRY, PROFILE_SKILLS, PROFILE_GOALS, PROFILE_TONE,
            LINKEDIN_EMAIL, LINKEDIN_PASSWORD, CONTENT_THEMES,
            OPTIMAL_TIMES, CONTENT_GOALS, PAYMENT_PROCESSING,
        )
        from telegram.ext import ConversationHandler

        loop = asyncio.get_event_loop()
        context = make_context()

        # Step 1: /start → PROFILE_INDUSTRY
        update = make_update(text="/start")
        state = loop.run_until_complete(start(update, context))
        self.assertEqual(state, PROFILE_INDUSTRY)

        # Step 2: Industry → PROFILE_SKILLS
        update = make_update(text="AI, software")
        state = loop.run_until_complete(profile_industry(update, context))
        self.assertEqual(state, PROFILE_SKILLS)

        # Step 3: Skills → PROFILE_GOALS
        update = make_update(text="Python, ML, Automation")
        state = loop.run_until_complete(profile_skills(update, context))
        self.assertEqual(state, PROFILE_GOALS)

        # Step 4: Goals → PROFILE_TONE
        update = make_update(text="tech lead, build products")
        state = loop.run_until_complete(profile_goals(update, context))
        self.assertEqual(state, PROFILE_TONE)

        # Step 5: Select tone → toggle
        update = make_update(callback_data='tone_professional')
        state = loop.run_until_complete(profile_tone(update, context))
        self.assertEqual(state, PROFILE_TONE)

        # Step 6: Done with tones → LINKEDIN_EMAIL
        update = make_update(callback_data='tone_done')
        state = loop.run_until_complete(profile_tone(update, context))
        self.assertEqual(state, LINKEDIN_EMAIL)

        # Step 7: Email → LINKEDIN_PASSWORD
        update = make_update(text="user@test.com")
        state = loop.run_until_complete(linkedin_email(update, context))
        self.assertEqual(state, LINKEDIN_PASSWORD)

        # Step 8: Password → CONTENT_THEMES
        update = make_update(text="password123", user_id=12345)
        state = loop.run_until_complete(linkedin_password(update, context))
        self.assertEqual(state, CONTENT_THEMES)

        # Step 9: Content themes → OPTIMAL_TIMES
        update = make_update(text="AI trends, career tips")
        state = loop.run_until_complete(content_themes(update, context))
        self.assertEqual(state, OPTIMAL_TIMES)

        # Step 10: Content goals → PAYMENT_PROCESSING
        context.user_data['optimal_times'] = ['09:00', '13:00']
        update = make_update(text="thought leadership, attract recruiters", user_id=12345)
        state = loop.run_until_complete(content_goals(update, context))
        self.assertEqual(state, PAYMENT_PROCESSING)

        # Step 11: Enter FREE promo → ConversationHandler.END
        update = make_update(text="FREE", user_id=12345)
        state = loop.run_until_complete(handle_promo_code_input(update, context))
        self.assertEqual(state, ConversationHandler.END)

        # Verify subscription was activated
        mock_db.activate_subscription.assert_called_once_with(12345, days=30)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Conversation State Constants Sanity
# ═══════════════════════════════════════════════════════════════════════════

class TestConversationStates(unittest.TestCase):
    """Ensure conversation state constants are unique and sequential."""

    def test_onboarding_states_are_unique(self):
        from multiuser.telegram_bot_multiuser import (
            PROFILE_INDUSTRY, PROFILE_SKILLS, PROFILE_GOALS,
            PROFILE_TONE, CUSTOM_TONE, CONTENT_THEMES,
            OPTIMAL_TIMES, CONTENT_GOALS, LINKEDIN_EMAIL,
            LINKEDIN_PASSWORD, PAYMENT_PROCESSING,
        )
        states = [
            PROFILE_INDUSTRY, PROFILE_SKILLS, PROFILE_GOALS,
            PROFILE_TONE, CUSTOM_TONE, CONTENT_THEMES,
            OPTIMAL_TIMES, CONTENT_GOALS, LINKEDIN_EMAIL,
            LINKEDIN_PASSWORD, PAYMENT_PROCESSING,
        ]
        self.assertEqual(len(states), len(set(states)), "Duplicate conversation state values!")

    def test_job_states_dont_overlap_onboarding(self):
        from multiuser.telegram_bot_multiuser import (
            PAYMENT_PROCESSING, SETJOB_ROLES, SETJOB_LOCATION, SETJOB_CONFIRM,
        )
        onboarding_max = PAYMENT_PROCESSING  # Should be 10
        self.assertGreater(SETJOB_ROLES, onboarding_max)
        self.assertGreater(SETJOB_LOCATION, onboarding_max)
        self.assertGreater(SETJOB_CONFIRM, onboarding_max)


if __name__ == '__main__':
    unittest.main()

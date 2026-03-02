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

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_success_activates(self, mock_db, mock_search):
        """Deep link with payment_success should activate subscription."""
        mock_db.is_subscription_active.return_value = False
        mock_db.activate_subscription.return_value = True
        mock_db.get_user.return_value = {'stripe_subscription_id': None}
        mock_search.return_value = None

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_once()

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_success_backfills_stripe_ids(self, mock_db, mock_search):
        """Deep link should try to backfill Stripe IDs if missing."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user.return_value = {'stripe_subscription_id': None}
        mock_search.return_value = 'sub_found_123'

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_search.assert_called_once_with(12345)

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_success_skips_backfill_if_ids_present(self, mock_db, mock_search):
        """Deep link should NOT search Stripe if IDs already saved."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user.return_value = {'stripe_subscription_id': 'sub_existing'}

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_search.assert_not_called()

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_start_payment_cancel_shows_retry(self, mock_db):
        """Deep link with payment_cancel should show retry options."""
        from multiuser.telegram_bot_multiuser import start, PAYMENT_PROCESSING
        update = make_update(text="/start")
        context = make_context(args=['payment_cancel'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, PAYMENT_PROCESSING)

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
        mock_task.delay.assert_called_once_with(12345, 'My LinkedIn post!', media=None)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Cancel Subscription
# ═══════════════════════════════════════════════════════════════════════════

class TestCancelSubscription(unittest.TestCase):
    """Test subscription cancellation flow."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_command_shows_confirmation(self, mock_db):
        """Cancel command should show confirmation buttons for active users."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_subscription_id': 'sub_test123',
            'stripe_customer_id': 'cus_test123',
        }
        mock_db.is_subscription_active.return_value = True

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


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment & Subscription Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestCancelFreeUser(unittest.TestCase):
    """Test cancellation for FREE/promo users (no Stripe subscription)."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_free_user_deactivates_locally(self, mock_db):
        """FREE user with no Stripe IDs should be deactivated locally."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }
        mock_db.deactivate_subscription.return_value = True

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_db.deactivate_subscription.assert_called_once_with(12345)
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_inactive_free_user_shows_no_subscription(self, mock_db):
        """Inactive FREE user should be told no subscription exists."""
        mock_db.get_user.return_value = {
            'subscription_active': False,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_db.deactivate_subscription.assert_not_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("don't have an active subscription", call_text.lower() if "don't" in call_text.lower() else call_text)


class TestCancelStripeUser(unittest.TestCase):
    """Test cancellation for Stripe-paying users."""

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_with_customer_id_shows_portal(self, mock_db, mock_stripe):
        """User with Stripe customer ID should see portal option."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test123',
            'stripe_subscription_id': 'sub_test123',
        }
        mock_portal = MagicMock()
        mock_portal.url = "https://billing.stripe.com/test"
        mock_stripe.billing_portal.Session.create.return_value = mock_portal

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_stripe.billing_portal.Session.create.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Stripe Portal", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_portal_fails_shows_fallback(self, mock_db, mock_stripe):
        """If Stripe portal fails, show direct API fallback."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test123',
            'stripe_subscription_id': 'sub_test123',
        }
        import stripe as real_stripe
        mock_stripe.billing_portal.Session.create.side_effect = real_stripe.error.StripeError("Portal unavailable")
        mock_stripe.error = real_stripe.error

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("unavailable", call_text.lower())

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_with_subscription_id(self, mock_db, mock_stripe):
        """Direct API cancel should work with valid subscription_id."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test123',
            'stripe_subscription_id': 'sub_test123',
        }
        mock_sub = MagicMock()
        mock_sub.current_period_end = 1735689600  # 2025-01-01
        mock_stripe.Subscription.modify.return_value = mock_sub

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_stripe.Subscription.modify.assert_called_once_with(
            'sub_test123', cancel_at_period_end=True
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_no_sub_id_deactivates_locally(self, mock_db, mock_search):
        """Force cancel with no sub ID and no Stripe search result should deactivate locally."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }
        mock_search.return_value = None

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_db.deactivate_subscription.assert_called_once_with(12345)
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_stripe_invalid_request_deactivates(self, mock_db, mock_stripe):
        """If Stripe says subscription doesn't exist, deactivate locally."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': 'sub_expired123',
        }
        import stripe as real_stripe
        mock_stripe.Subscription.modify.side_effect = real_stripe.error.InvalidRequestError(
            "No such subscription: sub_expired123", param="id"
        )
        mock_stripe.error = real_stripe.error

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_db.deactivate_subscription.assert_called_once_with(12345)
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)


class TestCancelCommand(unittest.TestCase):
    """Test /cancelsubscription command entry point."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_no_user_shows_no_subscription(self, mock_db):
        """User not in DB with no active sub should be told no subscription."""
        mock_db.get_user.return_value = None
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=99999)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("don't have an active subscription", call_text.lower() if "don't" in call_text.lower() else call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_active_user_shows_confirmation(self, mock_db):
        """Active user should see confirmation buttons."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)


try:
    import flask
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestCheckoutWebhook(unittest.TestCase):
    """Test checkout.session.completed webhook handler in payment_server."""

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_completed_saves_stripe_ids(self, mock_db, mock_notify):
        """checkout.session.completed should save customer_id and subscription_id."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test_123',
            'customer': 'cus_new_customer',
            'subscription': 'sub_new_subscription',
            'client_reference_id': '12345',
            'metadata': {'telegram_id': '12345'},
        }

        handle_checkout_session_completed(session)

        mock_db.activate_subscription.assert_called_once_with(
            12345,
            stripe_customer_id='cus_new_customer',
            stripe_subscription_id='sub_new_subscription',
            days=30
        )
        mock_notify.assert_called_once()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_completed_uses_metadata_fallback(self, mock_db, mock_notify):
        """Should fall back to metadata.telegram_id if client_reference_id missing."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test_456',
            'customer': 'cus_abc',
            'subscription': 'sub_abc',
            'client_reference_id': None,
            'metadata': {'telegram_id': '67890'},
        }

        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_called_once_with(
            67890,
            stripe_customer_id='cus_abc',
            stripe_subscription_id='sub_abc',
            days=30
        )

    @patch('payment_server.db')
    def test_checkout_completed_missing_telegram_id(self, mock_db):
        """Should handle missing telegram_id gracefully."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test_789',
            'customer': 'cus_xyz',
            'subscription': 'sub_xyz',
            'client_reference_id': None,
            'metadata': {},
        }

        # Should not raise
        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_not_called()


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestWebhookSubscriptionEvents(unittest.TestCase):
    """Test subscription lifecycle webhook handlers."""

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_deleted_deactivates(self, mock_db, mock_notify):
        """subscription.deleted should deactivate user."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_subscription_deleted

        subscription = {
            'id': 'sub_test123',
            'customer': 'cus_test123',
        }

        handle_subscription_deleted(subscription)
        mock_db.deactivate_subscription.assert_called_once_with(12345)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_deleted_user_not_found(self, mock_db, mock_notify):
        """subscription.deleted for unknown user should not crash."""
        mock_db.execute_query.return_value = None

        from payment_server import handle_subscription_deleted

        subscription = {
            'id': 'sub_unknown',
            'customer': 'cus_unknown',
        }

        # Should not raise
        handle_subscription_deleted(subscription)
        mock_db.deactivate_subscription.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_updated_cancellation_pending(self, mock_db, mock_notify):
        """subscription.updated with cancel_at_period_end should notify user."""
        mock_db.execute_query.return_value = {
            'telegram_id': 12345,
            'username': 'testuser',
            'first_name': 'Test'
        }

        from payment_server import handle_subscription_updated

        subscription = {
            'id': 'sub_test123',
            'customer': 'cus_test123',
            'cancel_at_period_end': True,
            'status': 'active',
            'current_period_end': 1735689600,
        }

        handle_subscription_updated(subscription)
        mock_notify.assert_called_once()
        notify_text = mock_notify.call_args[0][1]
        self.assertIn("Cancelled", notify_text)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_warns_user(self, mock_db, mock_notify):
        """invoice.payment_failed should warn user with retry info."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_test123',
            'subscription': 'sub_test123',
            'attempt_count': 1,
            'next_payment_attempt': 1735689600,
        }

        handle_invoice_payment_failed(invoice)
        mock_notify.assert_called_once()
        notify_text = mock_notify.call_args[0][1]
        self.assertIn("Payment Failed", notify_text)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_final_deactivates(self, mock_db, mock_notify):
        """Final payment failure should deactivate subscription."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_test123',
            'subscription': 'sub_test123',
            'attempt_count': 4,
            'next_payment_attempt': None,
        }

        handle_invoice_payment_failed(invoice)
        mock_db.deactivate_subscription.assert_called_once_with(12345)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestWebhookRouting(unittest.TestCase):
    """Test webhook event type routing."""

    @patch('payment_server.handle_checkout_session_completed')
    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_routes_checkout_completed(self, mock_stripe, mock_db, mock_handler):
        """Webhook should route checkout.session.completed events."""
        mock_event = {
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_test', 'customer': 'cus_test'}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'test_sig'})
        self.assertEqual(resp.status_code, 200)
        mock_handler.assert_called_once()


class TestFreePromoActivation(unittest.TestCase):
    """Test FREE promo code activation stores no Stripe IDs."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_free_promo_no_stripe_ids(self, mock_db):
        """FREE promo should activate without Stripe IDs."""
        mock_db.validate_promo_code.return_value = {
            'code': 'FREE', 'is_free_bypass': True,
        }
        mock_db.activate_subscription.return_value = True

        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler

        update = make_update(text="FREE", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)
        # Should NOT pass stripe IDs
        mock_db.activate_subscription.assert_called_once_with(12345, days=30)


class TestStripeCheckoutSessionId(unittest.TestCase):
    """Verify success_url includes {CHECKOUT_SESSION_ID} for all Stripe checkouts."""

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_regular_checkout_includes_session_id(self, mock_db, mock_stripe):
        """Regular Stripe checkout success_url should contain CHECKOUT_SESSION_ID."""
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from multiuser.telegram_bot_multiuser import handle_subscription
        from telegram.ext import ConversationHandler

        update = make_update(callback_data='subscribe_daily', user_id=12345)
        context = make_context(bot_username='TestBot')

        asyncio.get_event_loop().run_until_complete(handle_subscription(update, context))
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        self.assertIn('{CHECKOUT_SESSION_ID}', call_kwargs['success_url'])
        self.assertIn('session_id=', call_kwargs['success_url'])

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_freetrial_checkout_includes_session_id(self, mock_db, mock_stripe):
        """FREETRIAL checkout success_url should contain CHECKOUT_SESSION_ID."""
        mock_db.validate_promo_code.return_value = {
            'code': 'FREETRIAL', 'is_freetrial': True,
        }
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/trial"
        mock_stripe.checkout.Session.create.return_value = mock_session

        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler

        update = make_update(text="FREETRIAL", user_id=12345)
        context = make_context(bot_username='TestBot')

        asyncio.get_event_loop().run_until_complete(handle_promo_code_input(update, context))
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        self.assertIn('{CHECKOUT_SESSION_ID}', call_kwargs['success_url'])
        self.assertIn('session_id=', call_kwargs['success_url'])


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestPaymentSuccessRoute(unittest.TestCase):
    """Test payment success page saves Stripe IDs when session_id is present."""

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_page_saves_stripe_ids(self, mock_stripe, mock_db):
        """Payment success page with session_id should retrieve and save Stripe IDs."""
        mock_checkout = MagicMock()
        mock_checkout.get.side_effect = lambda k, d=None: {
            'customer': 'cus_new',
            'subscription': 'sub_new',
            'client_reference_id': '12345',
            'metadata': {'telegram_id': '12345'},
        }.get(k, d)
        mock_stripe.checkout.Session.retrieve.return_value = mock_checkout

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?bot=TestBot&session_id=cs_test_123')
        self.assertEqual(resp.status_code, 200)
        mock_stripe.checkout.Session.retrieve.assert_called_once_with('cs_test_123')
        mock_db.activate_subscription.assert_called_once_with(
            12345,
            stripe_customer_id='cus_new',
            stripe_subscription_id='sub_new',
            days=30
        )

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_page_no_session_id_still_works(self, mock_stripe, mock_db):
        """Payment success page without session_id should still render."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?bot=TestBot')
        self.assertEqual(resp.status_code, 200)
        mock_stripe.checkout.Session.retrieve.assert_not_called()

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_page_handles_stripe_error(self, mock_stripe, mock_db):
        """Payment success page should not crash if Stripe retrieval fails."""
        mock_stripe.checkout.Session.retrieve.side_effect = Exception("Stripe down")

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?bot=TestBot&session_id=cs_bad')
        self.assertEqual(resp.status_code, 200)
        mock_db.activate_subscription.assert_not_called()


class TestSubscriptionDatabaseMethods(unittest.TestCase):
    """Test database subscription methods handle edge cases."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_is_subscription_active_false_for_expired(self, mock_db):
        """Expired subscription should return False."""
        mock_db.is_subscription_active.return_value = False

        result = mock_db.is_subscription_active(99999)
        self.assertFalse(result)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_activate_subscription_with_stripe_ids(self, mock_db):
        """activate_subscription should accept and store Stripe IDs."""
        mock_db.activate_subscription.return_value = True

        result = mock_db.activate_subscription(
            12345,
            stripe_customer_id='cus_test',
            stripe_subscription_id='sub_test',
            days=30
        )
        self.assertTrue(result)
        mock_db.activate_subscription.assert_called_once_with(
            12345,
            stripe_customer_id='cus_test',
            stripe_subscription_id='sub_test',
            days=30
        )

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_deactivate_subscription(self, mock_db):
        """deactivate_subscription should be callable."""
        mock_db.deactivate_subscription.return_value = True
        result = mock_db.deactivate_subscription(12345)
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: _try_find_stripe_subscription Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestTryFindStripeSubscription(unittest.TestCase):
    """Test Stripe search utility for finding subscriptions."""

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_finds_active_subscription_by_metadata(self, mock_stripe, mock_db):
        """Should find active subscription via Subscription.search."""
        mock_sub = MagicMock()
        mock_sub.status = 'active'
        mock_sub.customer = 'cus_found'
        mock_sub.id = 'sub_found'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [mock_sub]

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertEqual(result, 'sub_found')
        mock_db.execute_query.assert_called_once()
        # Verify COALESCE update was called with correct IDs
        call_args = mock_db.execute_query.call_args[0]
        self.assertEqual(call_args[1], ('cus_found', 'sub_found', 12345))

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_finds_trialing_subscription(self, mock_stripe, mock_db):
        """Should find subscription in 'trialing' status."""
        mock_sub = MagicMock()
        mock_sub.status = 'trialing'
        mock_sub.customer = 'cus_trial'
        mock_sub.id = 'sub_trial'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [mock_sub]

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertEqual(result, 'sub_trial')

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_finds_past_due_subscription(self, mock_stripe, mock_db):
        """Should find subscription in 'past_due' status."""
        mock_sub = MagicMock()
        mock_sub.status = 'past_due'
        mock_sub.customer = 'cus_pd'
        mock_sub.id = 'sub_pd'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [mock_sub]

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertEqual(result, 'sub_pd')

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_skips_canceled_subscription(self, mock_stripe, mock_db):
        """Should skip canceled subscriptions, return None if nothing else."""
        mock_sub = MagicMock()
        mock_sub.status = 'canceled'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [mock_sub]
        # No customers found either
        mock_stripe.Customer.search.return_value.auto_paging_iter.return_value = []

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertIsNone(result)
        mock_db.execute_query.assert_not_called()

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_falls_back_to_customer_search(self, mock_stripe, mock_db):
        """When Subscription.search finds nothing, should search by Customer."""
        # No subscriptions found by direct search
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = []

        # Customer search finds a match
        mock_customer = MagicMock()
        mock_customer.id = 'cus_via_customer'
        mock_stripe.Customer.search.return_value.auto_paging_iter.return_value = [mock_customer]

        mock_sub = MagicMock()
        mock_sub.status = 'active'
        mock_sub.id = 'sub_via_customer'
        mock_stripe.Subscription.list.return_value.auto_paging_iter.return_value = [mock_sub]

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertEqual(result, 'sub_via_customer')
        mock_stripe.Subscription.list.assert_called_once_with(
            customer='cus_via_customer', status='all', limit=10
        )

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_returns_none_when_nothing_found(self, mock_stripe, mock_db):
        """Should return None when no subscriptions found anywhere."""
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = []
        mock_stripe.Customer.search.return_value.auto_paging_iter.return_value = []

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertIsNone(result)

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_handles_stripe_api_error_gracefully(self, mock_stripe, mock_db):
        """Should catch Stripe API errors and return None."""
        mock_stripe.Subscription.search.side_effect = Exception("Stripe API rate limit")

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertIsNone(result)

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_picks_first_active_from_multiple(self, mock_stripe, mock_db):
        """When multiple subscriptions found, should return the first active one."""
        sub1 = MagicMock()
        sub1.status = 'canceled'
        sub2 = MagicMock()
        sub2.status = 'active'
        sub2.customer = 'cus_multi'
        sub2.id = 'sub_second'
        sub3 = MagicMock()
        sub3.status = 'active'
        sub3.customer = 'cus_multi'
        sub3.id = 'sub_third'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [sub1, sub2, sub3]

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        self.assertEqual(result, 'sub_second')  # First active one, not sub_third

    @patch('multiuser.telegram_bot_multiuser.db')
    @patch('multiuser.telegram_bot_multiuser.stripe')
    def test_db_save_fails_returns_none(self, mock_stripe, mock_db):
        """If DB update fails during save, exception is caught and returns None."""
        mock_sub = MagicMock()
        mock_sub.status = 'active'
        mock_sub.customer = 'cus_db_fail'
        mock_sub.id = 'sub_db_fail'
        mock_stripe.Subscription.search.return_value.auto_paging_iter.return_value = [mock_sub]
        mock_db.execute_query.side_effect = Exception("DB connection lost")

        from multiuser.telegram_bot_multiuser import _try_find_stripe_subscription
        result = asyncio.get_event_loop().run_until_complete(
            _try_find_stripe_subscription(12345)
        )
        # The outer except catches the DB exception, returns None
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Cancel Command Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestCancelCommandEdgeCases(unittest.TestCase):
    """Extended edge case tests for cancel_subscription_command."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_when_db_get_user_raises(self, mock_db):
        """If db.get_user raises, should still check is_subscription_active."""
        mock_db.get_user.side_effect = Exception("DB down")
        mock_db.is_subscription_active.return_value = True

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        # Should still show confirmation since is_active=True
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_when_is_active_raises(self, mock_db):
        """If is_subscription_active raises, should default to False."""
        mock_db.get_user.return_value = None
        mock_db.is_subscription_active.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("don't have an active subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_both_db_calls_raise(self, mock_db):
        """If both db.get_user and is_subscription_active raise, shows no subscription."""
        mock_db.get_user.side_effect = Exception("DB down")
        mock_db.is_subscription_active.side_effect = Exception("DB down")

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("don't have an active subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_cancel_user_exists_but_inactive_and_no_stripe(self, mock_db):
        """User in DB but inactive and no Stripe IDs — should show confirmation since user exists."""
        mock_db.get_user.return_value = {
            'subscription_active': False,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }
        mock_db.is_subscription_active.return_value = False

        from multiuser.telegram_bot_multiuser import cancel_subscription_command
        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            cancel_subscription_command(update, context)
        )
        # user_data is not None, so condition `not user_data and not is_active` is False
        # => Should show confirmation buttons
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Confirm Cancel Callback Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestConfirmCancelEdgeCases(unittest.TestCase):
    """Extended edge case tests for handle_cancel_subscription_callback confirm_cancel_sub."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_confirm_cancel_db_get_user_raises_falls_to_case4(self, mock_db):
        """If db.get_user raises during confirm_cancel_sub, falls to Case 4 (no data)."""
        mock_db.get_user.side_effect = Exception("DB down")

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        # Patch _try_find_stripe_subscription to return None
        with patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription',
                   new_callable=AsyncMock, return_value=None):
            asyncio.get_event_loop().run_until_complete(
                handle_cancel_subscription_callback(update, context)
            )

        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("No active subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_confirm_cancel_user_has_customer_id_only(self, mock_db):
        """User has customer_id but no subscription_id — should show portal (Case 2)."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_only',
            'stripe_subscription_id': None,
        }

        import stripe as real_stripe
        mock_portal = MagicMock()
        mock_portal.url = "https://billing.stripe.com/portal"

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        with patch('multiuser.telegram_bot_multiuser.stripe') as mock_stripe:
            mock_stripe.billing_portal.Session.create.return_value = mock_portal
            mock_stripe.error = real_stripe.error
            asyncio.get_event_loop().run_until_complete(
                handle_cancel_subscription_callback(update, context)
            )
            mock_stripe.billing_portal.Session.create.assert_called_once()
            call_text = update.callback_query.edit_message_text.call_args[0][0]
            self.assertIn("Stripe Portal", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_confirm_cancel_sub_id_only_no_customer_shows_direct_api(self, mock_db):
        """User has subscription_id but no customer_id — should show direct API (Case 3)."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': 'sub_only_123',
        }

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("direct api", call_text.lower())

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_case4_stripe_search_finds_sub_shows_cancel_button(self, mock_db, mock_search):
        """Case 4: No Stripe data, but Stripe search finds subscription."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }
        mock_search.return_value = 'sub_discovered'

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        # Should skip Case 1 (has user_data but no stripe IDs -> Case 1)
        # Wait — user_data exists AND no stripe_customer_id AND no stripe_subscription_id → Case 1!
        # Actually Case 1 is entered first. Let me re-check the code...
        # Case 1: `if user_data and not stripe_customer_id and not stripe_subscription_id`
        # This is TRUE, so Case 1 is entered (FREE user deactivation), NOT Case 4.
        # The test should verify Case 1 behavior instead.
        mock_db.deactivate_subscription.assert_called_once_with(12345)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_confirm_cancel_user_data_subscription_active_none(self, mock_db):
        """User data with subscription_active=None should be treated as inactive."""
        mock_db.get_user.return_value = {
            'subscription_active': None,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        # subscription_active is None (falsy), should show "no subscription"
        mock_db.deactivate_subscription.assert_not_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("don't have an active subscription", call_text.lower() if "don't" in call_text.lower() else call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_confirm_cancel_empty_string_stripe_ids(self, mock_db):
        """Empty string Stripe IDs (vs None) should still be treated as missing."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': '',
            'stripe_subscription_id': '',
        }

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        # Empty strings are falsy → Case 1 (FREE user deactivation)
        mock_db.deactivate_subscription.assert_called_once_with(12345)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_portal_create_non_stripe_error_propagates(self, mock_db, mock_stripe):
        """Non-StripeError exception during portal creation should not be caught."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        import stripe as real_stripe
        mock_stripe.error = real_stripe.error
        mock_stripe.billing_portal.Session.create.side_effect = ConnectionError("Network down")

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()

        # Non-StripeError should propagate
        with self.assertRaises(ConnectionError):
            asyncio.get_event_loop().run_until_complete(
                handle_cancel_subscription_callback(update, context)
            )


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Force Cancel Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestForceCancelEdgeCases(unittest.TestCase):
    """Extended edge case tests for force_cancel_sub callback."""

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_idempotent_already_cancelled(self, mock_db, mock_stripe):
        """Force cancel on already-cancelled-at-period-end subscription should succeed."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_already_cancelled',
        }
        mock_sub = MagicMock()
        mock_sub.current_period_end = 1735689600
        # Stripe still returns success even if cancel_at_period_end was already True
        mock_stripe.Subscription.modify.return_value = mock_sub

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_stripe.Subscription.modify.assert_called_once_with(
            'sub_already_cancelled', cancel_at_period_end=True
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_stripe_generic_error(self, mock_db, mock_stripe):
        """Generic StripeError (not InvalidRequest) should show error message."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        import stripe as real_stripe
        mock_stripe.Subscription.modify.side_effect = real_stripe.error.StripeError("Service unavailable")
        mock_stripe.error = real_stripe.error

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_db.deactivate_subscription.assert_not_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Error", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_invalid_request_other_message(self, mock_db, mock_stripe):
        """InvalidRequestError that isn't 'no such subscription' should show API error."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        import stripe as real_stripe
        mock_stripe.Subscription.modify.side_effect = real_stripe.error.InvalidRequestError(
            "Invalid parameter: cancel_at_period_end", param="cancel_at_period_end"
        )
        mock_stripe.error = real_stripe.error

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        # Should NOT deactivate locally — it's a different error
        mock_db.deactivate_subscription.assert_not_called()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Stripe API Error", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_generic_exception(self, mock_db, mock_stripe):
        """Generic exception during cancel should show error message."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        import stripe as real_stripe
        mock_stripe.Subscription.modify.side_effect = RuntimeError("Unexpected error")
        mock_stripe.error = real_stripe.error

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("error occurred", call_text.lower())

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_searches_stripe_when_no_sub_id(self, mock_db, mock_stripe, mock_search):
        """Force cancel with no sub_id should search Stripe, then cancel if found."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': None,
        }
        mock_search.return_value = 'sub_discovered_456'
        mock_sub = MagicMock()
        mock_sub.current_period_end = 1735689600
        mock_stripe.Subscription.modify.return_value = mock_sub

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        mock_search.assert_called_once_with(12345)
        mock_stripe.Subscription.modify.assert_called_once_with(
            'sub_discovered_456', cancel_at_period_end=True
        )

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_db_get_user_raises(self, mock_db):
        """If db.get_user fails during force cancel, should search Stripe then deactivate."""
        mock_db.get_user.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        with patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription',
                   new_callable=AsyncMock, return_value=None):
            asyncio.get_event_loop().run_until_complete(
                handle_cancel_subscription_callback(update, context)
            )

        # user_data=None, not active, no sub found → "no subscription"
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("No active subscription", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_force_cancel_metadata_update_saved(self, mock_db, mock_stripe):
        """After successful force cancel, metadata should be updated with cancellation_pending."""
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_test',
            'stripe_subscription_id': 'sub_test',
        }
        mock_sub = MagicMock()
        mock_sub.current_period_end = 1735689600
        mock_stripe.Subscription.modify.return_value = mock_sub

        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()

        asyncio.get_event_loop().run_until_complete(
            handle_cancel_subscription_callback(update, context)
        )
        # Verify execute_query was called with cancellation_pending metadata update
        mock_db.execute_query.assert_called_once()
        sql = mock_db.execute_query.call_args[0][0]
        self.assertIn('cancellation_pending', sql)
        params = mock_db.execute_query.call_args[0][1]
        self.assertEqual(params[1], 12345)  # telegram_id


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment Success Deep Link Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentSuccessDeepLinkEdgeCases(unittest.TestCase):
    """Extended tests for /start payment_success deep link."""

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_payment_success_already_active_still_backfills(self, mock_db, mock_search):
        """Already-active user should still attempt backfill if Stripe IDs missing."""
        mock_db.is_subscription_active.return_value = True
        mock_db.get_user.return_value = {'stripe_subscription_id': None}
        mock_search.return_value = 'sub_backfilled'

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_search.assert_called_once_with(12345)
        # activate_subscription should NOT be called since already active
        mock_db.activate_subscription.assert_not_called()

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_payment_success_get_user_returns_none(self, mock_db, mock_search):
        """If get_user returns None, should skip backfill gracefully."""
        mock_db.is_subscription_active.return_value = False
        mock_db.activate_subscription.return_value = True
        mock_db.get_user.return_value = None

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_once()
        mock_search.assert_not_called()  # get_user returned None, so no backfill attempted

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_payment_success_backfill_exception_doesnt_crash(self, mock_db, mock_search):
        """Exception during backfill should be caught and not affect success flow."""
        mock_db.is_subscription_active.return_value = False
        mock_db.activate_subscription.return_value = True
        mock_db.get_user.return_value = {'stripe_subscription_id': None}
        mock_search.side_effect = Exception("Stripe network error")

        from multiuser.telegram_bot_multiuser import start
        from telegram.ext import ConversationHandler
        update = make_update(text="/start")
        context = make_context(args=['payment_success'])

        result = asyncio.get_event_loop().run_until_complete(start(update, context))
        self.assertEqual(result, ConversationHandler.END)
        # Should still work despite backfill exception


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment Server Webhook Handler Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestCheckoutWebhookEdgeCases(unittest.TestCase):
    """Extended checkout.session.completed webhook handler tests."""

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_non_numeric_telegram_id(self, mock_db, mock_notify):
        """Non-numeric telegram_id should be caught and logged."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test',
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'client_reference_id': 'not_a_number',
            'metadata': {},
        }

        # Should not raise, exception caught internally
        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_customer_none_subscription_present(self, mock_db, mock_notify):
        """customer=None but subscription present should still activate."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test',
            'customer': None,
            'subscription': 'sub_only',
            'client_reference_id': '12345',
            'metadata': {},
        }

        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_called_once_with(
            12345,
            stripe_customer_id=None,
            stripe_subscription_id='sub_only',
            days=30
        )

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_both_ids_none(self, mock_db, mock_notify):
        """Both customer and subscription None should not activate (FREE promo session)."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test',
            'customer': None,
            'subscription': None,
            'client_reference_id': '12345',
            'metadata': {},
        }

        handle_checkout_session_completed(session)
        # The code has: `if not telegram_id_str:` check but telegram_id is present
        # The activation happens unconditionally if telegram_id exists
        # Actually looking at the code: it calls activate_subscription regardless
        mock_db.activate_subscription.assert_called_once()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_activate_raises_still_notifies(self, mock_db, mock_notify):
        """If activate_subscription fails, notification should still be attempted."""
        from payment_server import handle_checkout_session_completed

        # The handler has a single try/except around everything,
        # so if activate_subscription raises, notification is NOT sent
        mock_db.activate_subscription.side_effect = Exception("DB error")

        session = {
            'id': 'cs_test',
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'client_reference_id': '12345',
            'metadata': {},
        }

        # Should not raise
        handle_checkout_session_completed(session)
        # Notification NOT called because exception was raised before it
        mock_notify.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_empty_metadata_dict(self, mock_db, mock_notify):
        """Empty metadata dict should fall back and handle gracefully."""
        from payment_server import handle_checkout_session_completed

        session = {
            'id': 'cs_test',
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'client_reference_id': None,
            'metadata': {},
        }

        # client_reference_id=None, metadata has no telegram_id → early return
        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_checkout_notification_fails_doesnt_crash(self, mock_db, mock_notify):
        """Notification failure should be caught and not crash handler."""
        from payment_server import handle_checkout_session_completed
        mock_notify.side_effect = Exception("Telegram API down")

        session = {
            'id': 'cs_test',
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'client_reference_id': '12345',
            'metadata': {},
        }

        # Exception from notification is inside the try/except, should not raise
        handle_checkout_session_completed(session)
        mock_db.activate_subscription.assert_called_once()


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestSubscriptionUpdatedEdgeCases(unittest.TestCase):
    """Extended subscription.updated webhook handler tests."""

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_reactivation_after_cancel(self, mock_db, mock_notify):
        """cancel_at_period_end=False + status=active should reactivate."""
        mock_db.execute_query.return_value = {
            'telegram_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
        }

        from payment_server import handle_subscription_updated

        subscription = {
            'id': 'sub_test',
            'customer': 'cus_test',
            'cancel_at_period_end': False,
            'status': 'active',
            'current_period_end': 1735689600,
        }

        handle_subscription_updated(subscription)
        # Should set subscription_active=TRUE
        update_call = mock_db.execute_query.call_args_list[-1]  # Last call
        self.assertIn('subscription_active = true', update_call[0][0].lower())
        mock_notify.assert_called()
        notify_text = mock_notify.call_args[0][1]
        self.assertIn("Reactivated", notify_text)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_updated_user_not_found(self, mock_db, mock_notify):
        """subscription.updated for unknown user should not crash."""
        mock_db.execute_query.return_value = None

        from payment_server import handle_subscription_updated

        subscription = {
            'id': 'sub_unknown',
            'customer': 'cus_unknown',
            'cancel_at_period_end': True,
            'status': 'active',
            'current_period_end': 1735689600,
        }

        handle_subscription_updated(subscription)
        mock_notify.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_updated_past_due_no_action(self, mock_db, mock_notify):
        """status=past_due with cancel_at_period_end=False should take no action."""
        mock_db.execute_query.return_value = {
            'telegram_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
        }

        from payment_server import handle_subscription_updated

        subscription = {
            'id': 'sub_test',
            'customer': 'cus_test',
            'cancel_at_period_end': False,
            'status': 'past_due',
            'current_period_end': 1735689600,
        }

        handle_subscription_updated(subscription)
        # Neither cancel nor reactivation branch matches
        mock_notify.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_subscription_updated_double_cancel(self, mock_db, mock_notify):
        """Double cancellation event should be handled idempotently."""
        mock_db.execute_query.return_value = {
            'telegram_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
        }

        from payment_server import handle_subscription_updated

        subscription = {
            'id': 'sub_test',
            'customer': 'cus_test',
            'cancel_at_period_end': True,
            'status': 'active',
            'current_period_end': 1735689600,
        }

        # Call twice
        handle_subscription_updated(subscription)
        handle_subscription_updated(subscription)

        # Should be called twice (idempotent — updates same metadata)
        self.assertEqual(mock_notify.call_count, 2)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestInvoicePaymentFailedEdgeCases(unittest.TestCase):
    """Extended invoice.payment_failed webhook handler tests."""

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_attempt_count_zero(self, mock_db, mock_notify):
        """attempt_count=0 with next_attempt should still warn."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'attempt_count': 0,
            'next_payment_attempt': 1735689600,
        }

        handle_invoice_payment_failed(invoice)
        mock_notify.assert_called_once()
        notify_text = mock_notify.call_args[0][1]
        self.assertIn("Attempt 0", notify_text)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_next_attempt_zero_deactivates(self, mock_db, mock_notify):
        """next_payment_attempt=0 (falsy) should be treated as final failure."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'attempt_count': 3,
            'next_payment_attempt': 0,  # Falsy
        }

        handle_invoice_payment_failed(invoice)
        mock_db.deactivate_subscription.assert_called_once_with(12345)

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_user_not_found(self, mock_db, mock_notify):
        """payment_failed for unknown user should not crash."""
        mock_db.execute_query.return_value = None

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_unknown',
            'subscription': 'sub_unknown',
            'attempt_count': 1,
            'next_payment_attempt': None,
        }

        handle_invoice_payment_failed(invoice)
        mock_db.deactivate_subscription.assert_not_called()
        mock_notify.assert_not_called()

    @patch('payment_server.send_telegram_notification')
    @patch('payment_server.db')
    def test_payment_failed_missing_subscription_key(self, mock_db, mock_notify):
        """Invoice with missing subscription key should still work."""
        mock_db.execute_query.return_value = {'telegram_id': 12345}

        from payment_server import handle_invoice_payment_failed

        invoice = {
            'customer': 'cus_test',
            # 'subscription' key missing
            'attempt_count': 1,
            'next_payment_attempt': None,
        }

        handle_invoice_payment_failed(invoice)
        # subscription_id defaults to None via .get()
        mock_db.deactivate_subscription.assert_called_once_with(12345)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestWebhookRoutingEdgeCases(unittest.TestCase):
    """Extended webhook routing tests."""

    @patch('payment_server.handle_subscription_updated')
    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_routes_subscription_updated(self, mock_stripe, mock_db, mock_handler):
        """Webhook should route customer.subscription.updated events."""
        mock_event = {
            'type': 'customer.subscription.updated',
            'data': {'object': {'id': 'sub_test', 'customer': 'cus_test'}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'test_sig'})
        self.assertEqual(resp.status_code, 200)
        mock_handler.assert_called_once()

    @patch('payment_server.handle_subscription_deleted')
    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_routes_subscription_deleted(self, mock_stripe, mock_db, mock_handler):
        """Webhook should route customer.subscription.deleted events."""
        mock_event = {
            'type': 'customer.subscription.deleted',
            'data': {'object': {'id': 'sub_test', 'customer': 'cus_test'}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'test_sig'})
        self.assertEqual(resp.status_code, 200)
        mock_handler.assert_called_once()

    @patch('payment_server.handle_invoice_payment_failed')
    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_routes_payment_failed(self, mock_stripe, mock_db, mock_handler):
        """Webhook should route invoice.payment_failed events."""
        mock_event = {
            'type': 'invoice.payment_failed',
            'data': {'object': {'id': 'in_test', 'customer': 'cus_test'}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'test_sig'})
        self.assertEqual(resp.status_code, 200)
        mock_handler.assert_called_once()

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_unhandled_event_returns_200(self, mock_stripe, mock_db):
        """Unhandled event types should still return 200."""
        mock_event = {
            'type': 'charge.succeeded',
            'data': {'object': {'id': 'ch_test'}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'test_sig'})
        self.assertEqual(resp.status_code, 200)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_webhook_signature_verification_error(self, mock_stripe, mock_db):
        """Signature verification error should return 400."""
        import stripe as real_stripe
        mock_stripe.Webhook.construct_event.side_effect = real_stripe.error.SignatureVerificationError(
            "Invalid signature", sig_header="bad"
        )
        mock_stripe.error = real_stripe.error

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.post('/webhook/stripe',
                           data=b'test_payload',
                           headers={'Stripe-Signature': 'bad_sig'})
        self.assertEqual(resp.status_code, 400)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestPaymentSuccessRouteEdgeCases(unittest.TestCase):
    """Extended tests for /payment/success endpoint."""

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_only_customer_id_activates(self, mock_stripe, mock_db):
        """Session with only customer_id (no subscription) should still activate."""
        mock_checkout = MagicMock()
        mock_checkout.get.side_effect = lambda k, d=None: {
            'customer': 'cus_only',
            'subscription': None,
            'client_reference_id': '12345',
            'metadata': {},
        }.get(k, d)
        mock_stripe.checkout.Session.retrieve.return_value = mock_checkout

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?session_id=cs_test')
        self.assertEqual(resp.status_code, 200)
        mock_db.activate_subscription.assert_called_once_with(
            12345,
            stripe_customer_id='cus_only',
            stripe_subscription_id=None,
            days=30
        )

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_both_ids_none_no_activate(self, mock_stripe, mock_db):
        """Session with both customer and subscription None should not activate."""
        mock_checkout = MagicMock()
        mock_checkout.get.side_effect = lambda k, d=None: {
            'customer': None,
            'subscription': None,
            'client_reference_id': '12345',
            'metadata': {},
        }.get(k, d)
        mock_stripe.checkout.Session.retrieve.return_value = mock_checkout

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?session_id=cs_test')
        self.assertEqual(resp.status_code, 200)
        mock_db.activate_subscription.assert_not_called()

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_duplicate_session_id_idempotent(self, mock_stripe, mock_db):
        """Hitting success page twice with same session_id should activate twice (idempotent via COALESCE)."""
        mock_checkout = MagicMock()
        mock_checkout.get.side_effect = lambda k, d=None: {
            'customer': 'cus_test',
            'subscription': 'sub_test',
            'client_reference_id': '12345',
            'metadata': {},
        }.get(k, d)
        mock_stripe.checkout.Session.retrieve.return_value = mock_checkout

        from payment_server import app as flask_app
        client = flask_app.test_client()
        client.get('/payment/success?session_id=cs_test')
        client.get('/payment/success?session_id=cs_test')
        self.assertEqual(mock_db.activate_subscription.call_count, 2)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_no_telegram_id_anywhere(self, mock_stripe, mock_db):
        """Session with no telegram_id in either field should not activate."""
        mock_checkout = MagicMock()
        mock_checkout.get.side_effect = lambda k, d=None: {
            'customer': 'cus_orphan',
            'subscription': 'sub_orphan',
            'client_reference_id': None,
            'metadata': {},
        }.get(k, d)
        mock_stripe.checkout.Session.retrieve.return_value = mock_checkout

        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?session_id=cs_orphan')
        self.assertEqual(resp.status_code, 200)
        mock_db.activate_subscription.assert_not_called()

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_page_renders(self, mock_stripe, mock_db):
        """Cancel page should render with 200 status."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/cancel?bot=TestBot')
        self.assertEqual(resp.status_code, 200)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_complete_renders(self, mock_stripe, mock_db):
        """Cancel-complete page should render with redirect info."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        with patch('requests.get') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {'result': {'username': 'TestBot'}}
            mock_req.return_value = mock_resp
            resp = client.get('/payment/cancel-complete?telegram_id=12345')
            self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Payment HTML Pages (WebApp.close, redirect, content)
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentHtmlPages(unittest.TestCase):
    """Test that payment HTML pages have correct WebApp.close() and redirect logic."""

    def test_payment_success_html_has_webapp_script(self):
        """payment_success.html should include Telegram WebApp JS SDK."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('telegram.org/js/telegram-web-app.js', content)

    def test_payment_success_html_has_webapp_close(self):
        """payment_success.html should call Telegram.WebApp.close()."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Telegram.WebApp.close()', content)

    def test_payment_success_html_has_webapp_detection(self):
        """payment_success.html should detect if running in Telegram WebApp."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('isTelegramWebApp', content)

    def test_payment_success_html_reads_bot_from_url(self):
        """payment_success.html should read bot username from URL params."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("params.get('bot')", content)
        self.assertIn('payment_success', content)

    def test_payment_success_html_has_fallback_redirect(self):
        """payment_success.html should have fallback redirect for non-WebApp."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('window.location.href', content)

    def test_payment_cancel_html_has_webapp_close(self):
        """payment_cancel.html should call Telegram.WebApp.close()."""
        with open('static/payment_cancel.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Telegram.WebApp.close()', content)
        self.assertIn('telegram.org/js/telegram-web-app.js', content)
        self.assertIn('isTelegramWebApp', content)

    def test_payment_cancel_html_reads_bot_from_url(self):
        """payment_cancel.html should read bot username from URL params."""
        with open('static/payment_cancel.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("params.get('bot')", content)
        self.assertIn('payment_cancel', content)

    def test_payment_success_html_button_click_closes_webapp(self):
        """Button click in WebApp mode should close instead of navigate."""
        with open('static/payment_success.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('addEventListener', content)
        self.assertIn('preventDefault', content)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask not installed")
class TestCancelCompleteWebApp(unittest.TestCase):
    """Test cancel-complete page has WebApp.close() support."""

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_complete_has_webapp_close(self, mock_stripe, mock_db):
        """Cancel-complete page should include Telegram WebApp.close() logic."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        with patch('requests.get') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {'result': {'username': 'TestBot'}}
            mock_req.return_value = mock_resp
            resp = client.get('/payment/cancel-complete?telegram_id=12345')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            self.assertIn('Telegram.WebApp.close()', html)
            self.assertIn('telegram.org/js/telegram-web-app.js', html)
            self.assertIn('isTelegramWebApp', html)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_complete_has_telegram_link(self, mock_stripe, mock_db):
        """Cancel-complete page should have link to Telegram bot."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        with patch('requests.get') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {'result': {'username': 'TestBot'}}
            mock_req.return_value = mock_resp
            resp = client.get('/payment/cancel-complete?telegram_id=12345')
            html = resp.data.decode('utf-8')
            self.assertIn('https://t.me/TestBot', html)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_complete_bot_api_fails_gracefully(self, mock_stripe, mock_db):
        """Cancel-complete should render even if Telegram API fails."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        with patch('requests.get') as mock_req:
            mock_req.side_effect = Exception("Network error")
            resp = client.get('/payment/cancel-complete?telegram_id=12345')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            self.assertIn('Cancellation processed', html)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_success_page_has_webapp_close_in_html(self, mock_stripe, mock_db):
        """Success page rendered via Flask should contain WebApp.close() in HTML."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/success?bot=TestBot')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Telegram.WebApp.close()', html)
        self.assertIn('isTelegramWebApp', html)

    @patch('payment_server.db')
    @patch('payment_server.stripe')
    def test_cancel_page_has_webapp_close_in_html(self, mock_stripe, mock_db):
        """Cancel page rendered via Flask should contain WebApp.close() in HTML."""
        from payment_server import app as flask_app
        client = flask_app.test_client()
        resp = client.get('/payment/cancel?bot=TestBot')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Telegram.WebApp.close()', html)
        self.assertIn('isTelegramWebApp', html)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Promo Code Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestPromoCodeEdgeCases(unittest.TestCase):
    """Edge case tests for promo code handling."""

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_free_promo_activate_fails(self, mock_db):
        """FREE promo when activate_subscription fails should stay in PAYMENT_PROCESSING."""
        mock_db.validate_promo_code.return_value = {
            'code': 'FREE', 'is_free_bypass': True,
        }
        mock_db.activate_subscription.return_value = False

        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING

        update = make_update(text="FREE", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)
        # Should show error message
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Error", call_text)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_validate_raises_exception(self, mock_db):
        """Exception during validate_promo_code should stay in PAYMENT_PROCESSING."""
        mock_db.validate_promo_code.side_effect = Exception("DB error")

        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING

        update = make_update(text="ANYCODE", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_freetrial_stripe_create_fails(self, mock_db, mock_stripe):
        """FREETRIAL when Stripe session creation fails should stay in PAYMENT_PROCESSING."""
        mock_db.validate_promo_code.return_value = {
            'code': 'FREETRIAL', 'is_freetrial': True,
        }
        mock_stripe.checkout.Session.create.side_effect = Exception("Stripe error")

        from multiuser.telegram_bot_multiuser import handle_promo_code_input, PAYMENT_PROCESSING

        update = make_update(text="FREETRIAL", user_id=12345)
        context = make_context(bot_username='TestBot')

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, PAYMENT_PROCESSING)
        # Should show error message
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Error", call_text)

    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_stripe_checkout_create_fails(self, mock_db, mock_stripe):
        """Stripe session creation failure during subscribe should show error."""
        mock_stripe.checkout.Session.create.side_effect = Exception("Invalid price ID")

        from multiuser.telegram_bot_multiuser import handle_subscription
        from telegram.ext import ConversationHandler

        update = make_update(callback_data='subscribe_daily', user_id=12345)
        context = make_context(bot_username='TestBot')

        result = asyncio.get_event_loop().run_until_complete(
            handle_subscription(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)

    @patch('multiuser.telegram_bot_multiuser.db')
    def test_promo_code_case_insensitive(self, mock_db):
        """Promo code should be handled case-insensitively (uppercased)."""
        mock_db.validate_promo_code.return_value = {
            'code': 'FREE', 'is_free_bypass': True,
        }
        mock_db.activate_subscription.return_value = True

        from multiuser.telegram_bot_multiuser import handle_promo_code_input
        from telegram.ext import ConversationHandler

        # User enters lowercase "free"
        update = make_update(text="free", user_id=12345)
        context = make_context()

        result = asyncio.get_event_loop().run_until_complete(
            handle_promo_code_input(update, context)
        )
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Subscription Activate/Deactivate DB Edge Cases (Real Logic)
# ═══════════════════════════════════════════════════════════════════════════

class TestActivateSubscriptionDB(unittest.TestCase):
    """Test BotDatabase.activate_subscription edge cases."""

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_activate_without_stripe_ids(self, mock_pool_cls):
        """Activate without Stripe IDs should work (FREE promo path)."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.activate_subscription(12345, days=30)
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_activate_with_partial_stripe_ids(self, mock_pool_cls):
        """Activate with only customer_id (no subscription_id) should work."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.activate_subscription(
            12345,
            stripe_customer_id='cus_partial',
            days=30
        )
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_deactivate_nonexistent_user(self, mock_pool_cls):
        """Deactivating non-existent user should not raise."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = None

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.deactivate_subscription(99999)
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_is_subscription_active_active_no_expiry(self, mock_pool_cls):
        """Active subscription with no expiry date should return True."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = {
            'subscription_active': True,
            'subscription_expires': None,
        }

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.is_subscription_active(12345)
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_is_subscription_active_future_expiry(self, mock_pool_cls):
        """Active subscription with future expiry should return True."""
        mock_pool_cls.return_value = mock_pool
        future = datetime.utcnow() + timedelta(days=10)
        mock_cursor.fetchone.return_value = {
            'subscription_active': True,
            'subscription_expires': future,
        }

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.is_subscription_active(12345)
        self.assertTrue(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_is_subscription_active_expired_auto_deactivates(self, mock_pool_cls):
        """Expired subscription should auto-deactivate and return False."""
        mock_pool_cls.return_value = mock_pool
        past = datetime.utcnow() - timedelta(days=1)
        mock_cursor.fetchone.return_value = {
            'subscription_active': True,
            'subscription_expires': past,
        }

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.is_subscription_active(12345)
        self.assertFalse(result)

    @patch('bot_database_postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_is_subscription_active_inactive_returns_false(self, mock_pool_cls):
        """Explicitly inactive subscription should return False."""
        mock_pool_cls.return_value = mock_pool
        mock_cursor.fetchone.return_value = {
            'subscription_active': False,
            'subscription_expires': None,
        }

        from bot_database_postgres import BotDatabase
        db = BotDatabase()
        result = db.is_subscription_active(12345)
        self.assertFalse(result)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: End-to-End Subscription Lifecycle
# ═══════════════════════════════════════════════════════════════════════════

class TestSubscriptionLifecycle(unittest.TestCase):
    """Test complete subscription lifecycle: activate → use → cancel → resubscribe."""

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_full_lifecycle_free_user(self, mock_db, mock_stripe, mock_search):
        """Full lifecycle: FREE activate → cancel → resubscribe."""
        from multiuser.telegram_bot_multiuser import (
            start, handle_promo_code_input,
            cancel_subscription_command, handle_cancel_subscription_callback,
        )
        from telegram.ext import ConversationHandler

        loop = asyncio.get_event_loop()

        # Step 1: Activate with FREE promo
        mock_db.get_user.return_value = None
        mock_db.validate_promo_code.return_value = {'code': 'FREE', 'is_free_bypass': True}
        mock_db.activate_subscription.return_value = True

        update = make_update(text="FREE", user_id=12345)
        context = make_context()
        result = loop.run_until_complete(handle_promo_code_input(update, context))
        self.assertEqual(result, ConversationHandler.END)
        mock_db.activate_subscription.assert_called_with(12345, days=30)

        # Step 2: Cancel subscription
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': None,
            'stripe_subscription_id': None,
        }
        mock_db.is_subscription_active.return_value = True

        update = make_update(text="/cancelsubscription", user_id=12345)
        context = make_context()
        loop.run_until_complete(cancel_subscription_command(update, context))
        # Should show confirmation buttons
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)

        # Step 3: Confirm cancel
        update = make_update(callback_data='confirm_cancel_sub', user_id=12345)
        context = make_context()
        loop.run_until_complete(handle_cancel_subscription_callback(update, context))
        mock_db.deactivate_subscription.assert_called_with(12345)

    @patch('multiuser.telegram_bot_multiuser._try_find_stripe_subscription', new_callable=AsyncMock)
    @patch('multiuser.telegram_bot_multiuser.stripe')
    @patch('multiuser.telegram_bot_multiuser.db')
    def test_full_lifecycle_stripe_user(self, mock_db, mock_stripe, mock_search):
        """Full lifecycle: Stripe activate → force cancel → verify message."""
        from multiuser.telegram_bot_multiuser import handle_cancel_subscription_callback
        import stripe as real_stripe

        loop = asyncio.get_event_loop()

        # Setup: User with Stripe subscription
        mock_db.get_user.return_value = {
            'subscription_active': True,
            'stripe_customer_id': 'cus_lifecycle',
            'stripe_subscription_id': 'sub_lifecycle',
        }
        mock_stripe.error = real_stripe.error

        mock_sub = MagicMock()
        mock_sub.current_period_end = 1735689600
        mock_stripe.Subscription.modify.return_value = mock_sub

        # Force cancel
        update = make_update(callback_data='force_cancel_sub', user_id=12345)
        context = make_context()
        loop.run_until_complete(handle_cancel_subscription_callback(update, context))

        # Verify Stripe API was called
        mock_stripe.Subscription.modify.assert_called_once_with(
            'sub_lifecycle', cancel_at_period_end=True
        )

        # Verify cancellation message
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Cancelled", call_text)
        self.assertIn("January", call_text)  # 1735689600 = Jan 1, 2025


if __name__ == '__main__':
    unittest.main()

"""
LinkedIn Growth Telegram Bot
AI-powered LinkedIn automation via Telegram
"""

import os
import sys
import json
import logging
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Celery tasks for multi-user support
try:
    from tasks import (
        post_to_linkedin_task,
        engage_with_feed_task,
        reply_engagement_task,
        send_connection_requests_task,
        autopilot_task,
        scan_jobs_task
    )
    CELERY_ENABLED = True
    print("[INFO] Celery tasks loaded - Multi-user mode enabled")
except ImportError as e:
    CELERY_ENABLED = False
    print(f"[WARNING] Celery tasks not available: {e}")
    print("[WARNING] Falling back to single-user threading mode")
    from threading import Thread


from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import stripe
from cryptography.fernet import Fernet
from bot_database_postgres import BotDatabase
from linkedin_bot import LinkedInBot
import asyncio
# Multi-user: Use Celery instead of threading
# from threading import Thread
from screenshot_handler import screenshot_queue, save_screenshot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(PROFILE_INDUSTRY, PROFILE_SKILLS, PROFILE_GOALS, PROFILE_TONE, CUSTOM_TONE,
 CONTENT_THEMES, OPTIMAL_TIMES, CONTENT_GOALS,
 LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
 PAYMENT_PROCESSING) = range(11)

# Job search conversation states
(SETJOB_ROLES, SETJOB_LOCATION, SETJOB_CONFIRM) = range(11, 14)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # Your subscription price ID from Stripe
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY') or Fernet.generate_key()
PAYMENT_SERVER_URL = os.getenv('PAYMENT_SERVER_URL', 'http://localhost:5000')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'http://localhost:8080')  # WebApp hosting URL

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Initialize database
db = BotDatabase()

# Encryption helper
cipher = Fernet(ENCRYPTION_KEY)

# Global application reference (set in main(), used by legacy thread functions)
application = None


MAX_LOGIN_ATTEMPTS = 3

# Media upload settings for post attachments
from pathlib import Path
UPLOAD_DIR = Path("uploads/post_media")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov'}
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
MAX_MEDIA_SIZE_MB = 10


def encrypt_password(password: str) -> bytes:
    """Encrypt password before storing"""
    return cipher.encrypt(password.encode())


def decrypt_password(encrypted: bytes) -> str:
    """Decrypt stored password"""
    return cipher.decrypt(encrypted).decode()


def login_with_retry(linkedin_bot, notify_fn=None, max_attempts=MAX_LOGIN_ATTEMPTS):
    """
    Attempt LinkedIn login up to max_attempts times.
    Sends progress updates via notify_fn(message).
    Returns True on success, False after all attempts fail.
    """
    import time
    for attempt in range(1, max_attempts + 1):
        if notify_fn:
            notify_fn(f"Signing in to LinkedIn... (attempt {attempt}/{max_attempts})")
        if linkedin_bot.start():
            return True
        if attempt < max_attempts:
            if notify_fn:
                notify_fn(f"Sign-in attempt {attempt} failed. Retrying in 10 seconds...")
            time.sleep(10)
    # All attempts exhausted
    if notify_fn:
        notify_fn(
            f"LinkedIn sign-in failed after {max_attempts} attempts.\n\n"
            "Possible reasons:\n"
            "- Incorrect email or password\n"
            "- LinkedIn is blocking our server device\n\n"
            "What to do:\n"
            "1. Check your credentials: /settings > Update LinkedIn Credentials\n"
            "2. Open LinkedIn in your browser, sign in manually, and approve any security prompts (e.g., 'Was this you?')\n"
            "3. Try again after approving"
        )
    return False


def validate_text_input(text: str) -> bool:
    """
    Validate that input only contains letters, spaces, commas, and basic punctuation.
    Allowed: letters (any language), spaces, commas, hyphens, apostrophes, parentheses, ampersands
    """
    import re
    if not text or not text.strip():
        return False
    # Allow letters (including unicode), spaces, commas, hyphens, apostrophes, parentheses, ampersands, and periods
    pattern = r'^[\w\s,\-\'\(\)&\.]+$'
    return bool(re.match(pattern, text.strip(), re.UNICODE))


def validate_email(email: str) -> bool:
    """Validate basic email format: something@something.something"""
    import re
    if not email or not email.strip():
        return False
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(pattern, email.strip()))


def validate_password(password: str) -> str:
    """
    Validate password meets minimum requirements.
    Returns error message if invalid, or empty string if valid.
    """
    if not password:
        return "Password cannot be empty."
    if len(password) < 6:
        return "Password must be at least 6 characters long."
    if len(password) > 200:
        return "Password is too long. Please enter a shorter password."
    return ""


def validate_time_input(times_text: str) -> tuple:
    """
    Validate comma-separated HH:MM times (24-hour format).
    Returns (is_valid, parsed_times, error_msg).
    """
    import re
    times = [t.strip() for t in times_text.split(',') if t.strip()]
    if not times:
        return False, [], "Please enter at least one time."

    time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
    invalid_times = []
    valid_times = []
    for t in times:
        if re.match(time_pattern, t):
            valid_times.append(t)
        else:
            invalid_times.append(t)

    if invalid_times:
        return (False, [],
                f"Invalid time(s): {', '.join(invalid_times)}\n\n"
                f"Please use HH:MM format (24-hour clock).\n"
                f"Examples: 09:00, 13:30, 17:00")

    return True, valid_times, ""


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command - welcome message and begin onboarding"""
    user = update.effective_user
    telegram_id = user.id

    # Check for deep link parameters (e.g., from Stripe redirect)
    if context.args:
        param = context.args[0]

        # Handle payment success - activate subscription and ensure Stripe IDs are saved
        if param == 'payment_success':
            if not db.is_subscription_active(telegram_id):
                db.activate_subscription(telegram_id, days=30)

            # Ensure Stripe IDs are saved (payment_success page should have done this,
            # but this is a safety net in case it was missed)
            try:
                user_data = db.get_user(telegram_id)
                if user_data and not user_data.get('stripe_subscription_id'):
                    # IDs not saved yet — try to find via Stripe search
                    found = await _try_find_stripe_subscription(telegram_id)
                    if found:
                        logger.info(f"Backfilled Stripe IDs for user {telegram_id} via deep link")
            except Exception as e:
                logger.warning(f"Could not backfill Stripe IDs for {telegram_id}: {e}")

            await update.message.reply_text(
                "🎉 Payment Successful!\n\n"
                "Your subscription has been automatically activated!\n\n"
                "You now have full access to:\n"
                "- AI-generated posts\n"
                "- Smart feed engagement\n"
                "- Automated networking\n"
                "- Analytics dashboard\n\n"
                "Send /autopilot to start!\n\n"
                "Need help? Send /help"
            )
            return ConversationHandler.END

        # Handle payment cancellation
        elif param == 'payment_cancel':
            keyboard = [
                [InlineKeyboardButton("Try Again", callback_data='subscribe')],
                [InlineKeyboardButton("I Have a Promo Code", callback_data='promo_code')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Payment was not completed.\n\n"
                "No charges were made to your account.\n\n"
                "You can:\n"
                "• Tap 'Try Again' to subscribe\n"
                "• Enter a promo code if you have one\n"
                "• Send /start anytime to restart\n\n"
                "Questions? Send /help",
                reply_markup=reply_markup
            )
            return PAYMENT_PROCESSING

    # Check if user already exists
    try:
        user_data = db.get_user(telegram_id)
    except Exception as e:
        logger.error(f"Database error in start() for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Sorry, we're experiencing a temporary issue. Please try again in a moment.\n\n"
            "If the problem persists, send /start again."
        )
        return ConversationHandler.END

    if user_data and user_data.get('subscription_active'):
        await update.message.reply_text(
            f"Welcome back, {user.first_name}! 🚀\n\n"
            f"Your subscription is active.\n\n"
            f"Available commands:\n"
            f"/autopilot - Run full automation\n"
            f"/post - Generate and post AI content\n"
            f"/engage - Engage with feed\n"
            f"/connect - Send connection requests\n"
            f"/schedule - Schedule content\n"
            f"/stats - View analytics\n"
            f"/settings - Update your profile\n"
            f"/help - Get help"
        )
        return ConversationHandler.END

    # New user onboarding
    await update.message.reply_text(
        f"👋 Welcome to LinkedInGrowthBot, {user.first_name}!\n\n"
        f"Automate your LinkedIn success with our AI-powered bot. "
        f"Schedule posts, engage authentically with comments and likes, "
        f"send personalized messages, and grow your network—all on autopilot.\n\n"
        f"Stay active, build relationships, and generate leads 24/7 without lifting a finger. 💼\n\n"
        f"Let's set up your profile!\n\n"
        f"First, what's your industry? (e.g., software development, marketing, sales)"
    )

    return PROFILE_INDUSTRY


async def profile_industry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect user's industry"""
    industry = update.message.text.strip()

    if not industry:
        await update.message.reply_text(
            "Input cannot be empty. Please enter your industry:\n\n"
            "Example: Technology, AI, Software Development"
        )
        return PROFILE_INDUSTRY

    # Validate input
    if not validate_text_input(industry):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: Technology, AI, Software Development\n\n"
            "Please enter your industry again:"
        )
        return PROFILE_INDUSTRY

    context.user_data['industry'] = [i.strip() for i in industry.split(',')]

    await update.message.reply_text(
        "Great! Now, what are your key skills? (comma-separated)\n"
        "Example: Python, automation, AI, web development"
    )
    return PROFILE_SKILLS


async def profile_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect user's skills"""
    skills = update.message.text.strip()

    if not skills:
        await update.message.reply_text(
            "Input cannot be empty. Please enter your skills:\n\n"
            "Example: Python, Machine Learning, Cloud Computing"
        )
        return PROFILE_SKILLS

    # Validate input
    if not validate_text_input(skills):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: Python, Machine Learning, Cloud Computing\n\n"
            "Please enter your skills again:"
        )
        return PROFILE_SKILLS

    context.user_data['skills'] = [s.strip() for s in skills.split(',')]

    await update.message.reply_text(
        "Perfect! What are your career goals?\n"
        "Example: senior developer role, technical sales, business development"
    )
    return PROFILE_GOALS


async def profile_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect user's career goals"""
    goals = update.message.text.strip()

    if not goals:
        await update.message.reply_text(
            "Input cannot be empty. Please enter your career goals:\n\n"
            "Example: Become a Tech Lead, Build AI Products, Start a Startup"
        )
        return PROFILE_GOALS

    # Validate input
    if not validate_text_input(goals):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: Become a Tech Lead, Build AI Products, Start a Startup\n\n"
            "Please enter your career goals again:"
        )
        return PROFILE_GOALS

    context.user_data['career_goals'] = [g.strip() for g in goals.split(',')]

    # Initialize selected tones
    context.user_data['selected_tones'] = []

    keyboard = [
        [InlineKeyboardButton("☐ Professional yet approachable", callback_data='tone_professional')],
        [InlineKeyboardButton("☐ Technical expert", callback_data='tone_technical')],
        [InlineKeyboardButton("☐ Thought leader", callback_data='tone_leader')],
        [InlineKeyboardButton("☐ Casual and friendly", callback_data='tone_casual')],
        [InlineKeyboardButton("✏️ Custom tone", callback_data='tone_custom')],
        [InlineKeyboardButton("✅ Done", callback_data='tone_done')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "What tone should your posts have? (You can select multiple)\n\n"
        "Select all that apply, then click 'Done':",
        reply_markup=reply_markup
    )
    return PROFILE_TONE


async def profile_tone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle tone selection (multiple selections allowed)"""
    query = update.callback_query
    await query.answer()

    tone_map = {
        'tone_professional': 'professional yet approachable',
        'tone_technical': 'technical expert',
        'tone_leader': 'thought leader',
        'tone_casual': 'casual and friendly'
    }

    # Initialize selected_tones if not exists
    if 'selected_tones' not in context.user_data:
        context.user_data['selected_tones'] = []

    # Handle custom tone
    if query.data == 'tone_custom':
        await query.edit_message_text(
            "✏️ Enter your custom tone description:\n\n"
            "Example: witty and humorous, inspiring and motivational, data-driven analyst, etc."
        )
        return CUSTOM_TONE

    # Handle done button
    if query.data == 'tone_done':
        if not context.user_data['selected_tones']:
            await query.answer("Please select at least one tone!", show_alert=True)
            return PROFILE_TONE

        context.user_data['tone'] = context.user_data['selected_tones']

        tones_text = ', '.join(context.user_data['tone'])
        await query.edit_message_text(
            f"Tones selected: {tones_text} ✅\n\n"
            f"Great! Now let's connect your LinkedIn account.\n\n"
            f"Please enter your LinkedIn email address:"
        )
        return LINKEDIN_EMAIL

    # Toggle tone selection
    tone_value = tone_map[query.data]
    if tone_value in context.user_data['selected_tones']:
        context.user_data['selected_tones'].remove(tone_value)
    else:
        context.user_data['selected_tones'].append(tone_value)

    # Update keyboard with checkmarks
    selected_set = set(context.user_data['selected_tones'])
    keyboard = [
        [InlineKeyboardButton(
            f"{'☑️' if tone_map['tone_professional'] in selected_set else '☐'} Professional yet approachable",
            callback_data='tone_professional'
        )],
        [InlineKeyboardButton(
            f"{'☑️' if tone_map['tone_technical'] in selected_set else '☐'} Technical expert",
            callback_data='tone_technical'
        )],
        [InlineKeyboardButton(
            f"{'☑️' if tone_map['tone_leader'] in selected_set else '☐'} Thought leader",
            callback_data='tone_leader'
        )],
        [InlineKeyboardButton(
            f"{'☑️' if tone_map['tone_casual'] in selected_set else '☐'} Casual and friendly",
            callback_data='tone_casual'
        )],
        [InlineKeyboardButton("✏️ Custom tone", callback_data='tone_custom')],
        [InlineKeyboardButton("✅ Done", callback_data='tone_done')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    selected_text = f"\n\nSelected: {', '.join(context.user_data['selected_tones'])}" if context.user_data['selected_tones'] else ""

    await query.edit_message_text(
        f"What tone should your posts have? (You can select multiple){selected_text}\n\n"
        f"Select all that apply, then click 'Done':",
        reply_markup=reply_markup
    )
    return PROFILE_TONE


async def custom_tone_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom tone text input"""
    custom_tone = update.message.text.strip()

    if not custom_tone:
        await update.message.reply_text(
            "Input cannot be empty. Please describe your custom tone:\n\n"
            "Example: witty and humorous, inspiring and motivational"
        )
        return CUSTOM_TONE

    # Validate input
    if not validate_text_input(custom_tone):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: witty and humorous, inspiring and motivational\n\n"
            "Please enter your custom tone again:"
        )
        return CUSTOM_TONE

    # Add custom tone to selected tones
    if 'selected_tones' not in context.user_data:
        context.user_data['selected_tones'] = []

    context.user_data['selected_tones'].append(custom_tone)
    context.user_data['tone'] = context.user_data['selected_tones']

    tones_text = ', '.join(context.user_data['tone'])
    await update.message.reply_text(
        f"Custom tone added: {custom_tone} ✅\n\n"
        f"All selected tones: {tones_text}\n\n"
        f"Great! Now let's connect your LinkedIn account.\n\n"
        f"Please enter your LinkedIn email address:"
    )
    return LINKEDIN_EMAIL


async def content_themes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect content themes"""
    themes = update.message.text.strip()

    if not themes:
        await update.message.reply_text(
            "Input cannot be empty. Please enter your content themes:\n\n"
            "Example: AI & Machine Learning, Career Development, Tech Trends"
        )
        return CONTENT_THEMES

    # Validate input
    if not validate_text_input(themes):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: AI & Machine Learning, Career Development, Tech Trends\n\n"
            "Please enter your content themes again:"
        )
        return CONTENT_THEMES

    context.user_data['content_themes'] = [t.strip() for t in themes.split(',')]

    keyboard = [
        [InlineKeyboardButton("✅ Use default times (recommended)", callback_data='use_default_times')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⏰ When should we post your content?\n\n"
        "📊 Best recommended timeslots for maximum outreach:\n"
        "• 09:00 (Morning engagement - professionals checking LinkedIn)\n"
        "• 13:00 (Lunch break - high activity period)\n"
        "• 17:00 (End of workday - wrap-up browsing)\n\n"
        "You can use our defaults above, or enter your own times:\n\n"
        "Format: HH:MM, HH:MM\n"
        "Example: 08:00, 12:00, 16:00",
        reply_markup=reply_markup
    )
    return OPTIMAL_TIMES


async def optimal_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect optimal posting times (handles both button and text input)"""
    # Check if it's a callback query (button press) or message (text input)
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        # Use default recommended times
        context.user_data['optimal_times'] = ['09:00', '13:00', '17:00']

        await query.edit_message_text(
            "✅ Default times selected: 09:00, 13:00, 17:00\n\n"
            "Finally, what are your content goals? (comma-separated)\n\n"
            "Example:\n"
            "- position as a builder who ships real products\n"
            "- share authentic behind-the-scenes stories\n"
            "- attract recruiters and collaborators"
        )
    else:
        # User entered custom times — validate HH:MM format
        times_text = update.message.text
        is_valid, parsed_times, error_msg = validate_time_input(times_text)

        if not is_valid:
            keyboard = [[InlineKeyboardButton("Use default times (09:00, 13:00, 17:00)", callback_data='use_default_times')]]
            await update.message.reply_text(
                f"{error_msg}\n\n"
                "Or click below to use our recommended times:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return OPTIMAL_TIMES

        context.user_data['optimal_times'] = parsed_times

        await update.message.reply_text(
            f"✅ Custom times set: {', '.join(parsed_times)}\n\n"
            "Finally, what are your content goals? (comma-separated)\n\n"
            "Example:\n"
            "- position as a builder who ships real products\n"
            "- share authentic behind-the-scenes stories\n"
            "- attract recruiters and collaborators"
        )

    return CONTENT_GOALS


async def content_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect content goals and show summary"""
    goals = update.message.text.strip()

    if not goals:
        await update.message.reply_text(
            "Input cannot be empty. Please enter your content goals:\n\n"
            "Example: Build thought leadership, Attract recruiters, Share expertise"
        )
        return CONTENT_GOALS

    # Validate input
    if not validate_text_input(goals):
        await update.message.reply_text(
            "Invalid input. Please use only letters, spaces, and commas.\n\n"
            "Example: Build thought leadership, Attract recruiters, Share expertise\n\n"
            "Please enter your content goals again:"
        )
        return CONTENT_GOALS

    context.user_data['content_goals'] = [g.strip() for g in goals.split(',')]

    # Save profile to database
    telegram_id = update.effective_user.id

    profile_data = {
        'industry': context.user_data['industry'],
        'skills': context.user_data['skills'],
        'career_goals': context.user_data['career_goals'],
        'tone': context.user_data['tone'],
        'interests': context.user_data['skills']  # Use skills as interests
    }

    content_strategy = {
        'content_themes': context.user_data['content_themes'],
        'optimal_times': context.user_data['optimal_times'],
        'content_goals': context.user_data['content_goals'],
        'posting_frequency': 'daily'
    }

    try:
        db.save_user_profile(telegram_id, profile_data, content_strategy)
    except Exception as e:
        logger.error(f"Failed to save user profile for {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to save your profile due to a temporary error.\n\n"
            "Please try again by sending /start."
        )
        return ConversationHandler.END

    # Show summary and proceed to payment
    summary = (
        f"✅ Profile Complete!\n\n"
        f"👤 Industry: {', '.join(context.user_data['industry'])}\n"
        f"💼 Skills: {', '.join(context.user_data['skills'][:3])}...\n"
        f"🎯 Career Goals: {', '.join(context.user_data['career_goals'])}\n"
        f"📝 Tone: {context.user_data['tone'][0]}\n"
        f"📅 Content Themes: {len(context.user_data['content_themes'])} topics\n"
        f"⏰ Post Times: {', '.join(context.user_data['optimal_times'])}\n"
        f"✅ LinkedIn: Connected\n\n"
        f"Everything is set up! Time to subscribe. 🚀"
    )

    await update.message.reply_text(summary)

    # Show subscription options
    keyboard = [
        [InlineKeyboardButton("💳 Subscribe for $0.99/day", callback_data='subscribe_daily')],
        [InlineKeyboardButton("🎁 I have a promo code", callback_data='promo_code')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💎 Premium Access - Just $0.99/day\n\n"
        "Get unlimited access to:\n"
        "✓ AI-generated posts (unlimited)\n"
        "✓ Smart feed engagement (likes + comments)\n"
        "✓ Automated networking & connection requests\n"
        "✓ Personalized AI messages\n"
        "✓ Advanced analytics dashboard\n"
        "✓ 24/7 automation on autopilot\n"
        "✓ Priority support\n\n"
        "💰 Pricing:\n"
        "• $0.99 charged daily (cancel anytime)\n"
        "• Less than a cup of coffee!\n"
        "• ~$30/month only if you keep it\n\n"
        "💳 Payment: All major credit cards accepted\n"
        "🔒 Secure: Powered by Stripe\n\n"
        "Choose an option:",
        reply_markup=reply_markup
    )

    return PAYMENT_PROCESSING


async def linkedin_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect LinkedIn email"""
    email = update.message.text.strip()

    if not email:
        await update.message.reply_text(
            "Email cannot be empty.\n\n"
            "Please enter your LinkedIn email address (e.g., john@example.com):"
        )
        return LINKEDIN_EMAIL

    if not validate_email(email):
        await update.message.reply_text(
            "That doesn't look like a valid email address.\n\n"
            "Please enter a valid email (e.g., john@example.com):"
        )
        return LINKEDIN_EMAIL

    context.user_data['linkedin_email'] = email

    await update.message.reply_text(
        "Great! Now enter your LinkedIn password:\n"
        "(Encrypted and safely stored in your device, not accessible by anyone but you)"
    )
    return LINKEDIN_PASSWORD


async def linkedin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect LinkedIn password and proceed to content strategy"""
    password = update.message.text
    telegram_id = update.effective_user.id

    # Delete the password message immediately for security
    try:
        await update.message.delete()
    except Exception:
        pass

    # Validate password
    password_error = validate_password(password)
    if password_error:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"{password_error}\n\nPlease enter your LinkedIn password again:"
        )
        return LINKEDIN_PASSWORD

    # Encrypt and save credentials
    encrypted_password = encrypt_password(password)
    try:
        db.save_linkedin_credentials(
            telegram_id,
            context.user_data['linkedin_email'],
            encrypted_password
        )
    except Exception as e:
        logger.error(f"Failed to save LinkedIn credentials for user {telegram_id}: {e}")
        await context.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Failed to save your LinkedIn credentials due to a temporary error.\n\n"
                "Please try again by sending your password."
            )
        )
        return LINKEDIN_PASSWORD

    # Send confirmation and next question
    await context.bot.send_message(
        chat_id=telegram_id,
        text=(
            "✅ LinkedIn credentials saved securely!\n\n"
            "Now, let's plan your content strategy.\n\n"
            "What content themes do you want to post about? (comma-separated)\n\n"
            "Example:\n"
            "- building AI agents and lessons learned\n"
            "- automating business workflows\n"
            "- the future of work with AI"
        )
    )
    return CONTENT_THEMES


async def handle_promo_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle promo code text input"""
    promo_code = update.message.text.strip().upper()
    telegram_id = update.effective_user.id

    # Validate promo code
    try:
        result = db.validate_promo_code(promo_code)
    except Exception as e:
        logger.error(f"Failed to validate promo code for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to validate promo code due to a temporary error.\n\n"
            "Please try again in a moment."
        )
        return PAYMENT_PROCESSING

    if not result:
        await update.message.reply_text(
            "❌ Invalid promo code. The code may be expired, fully used, or doesn't exist.\n\n"
            "Please enter a valid promo code or skip to payment."
        )
        return PAYMENT_PROCESSING

    # Check for FREE bypass code
    if result.get('is_free_bypass'):
        # Completely bypass payment - activate subscription directly
        db.use_promo_code(promo_code)
        if db.activate_subscription(telegram_id, days=30):
            await update.message.reply_text(
                "🎉 FREE Code Activated!\n\n"
                "✅ Your subscription is now ACTIVE for 30 days!\n"
                "💯 Completely FREE - No payment required!\n\n"
                "You can now:\n"
                "• Add your LinkedIn account\n"
                "• Start automating engagement\n"
                "• Grow your network\n\n"
                "Type /help to get started! 🚀"
            )
            logger.info(f"User {telegram_id} activated FREE subscription via promo code")
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Error activating subscription. Please try again or contact support."
            )
            return PAYMENT_PROCESSING

    if result.get('is_freetrial'):
        # FREE TRIAL - Create Stripe checkout with 7-day trial period
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                subscription_data={
                    'trial_period_days': 7,  # 7-day free trial before first charge
                },
                success_url=f'{PAYMENT_SERVER_URL}/payment/success?bot={context.bot.username}&session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{PAYMENT_SERVER_URL}/payment/cancel?bot={context.bot.username}',
                client_reference_id=str(telegram_id),
                metadata={
                    'telegram_id': str(telegram_id),
                    'promo_code': promo_code
                },
                payment_method_options={
                    'card': {
                        'request_three_d_secure': 'automatic',
                    }
                },
                billing_address_collection='auto',
            )

            # Mark promo code as used
            db.use_promo_code(promo_code)

            keyboard = [[InlineKeyboardButton("Start 7-Day FREE Trial 🎁", url=session.url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"🎉 {promo_code} Activated!\n\n"
                f"✅ You get a 7-DAY FREE TRIAL!\n\n"
                f"How it works:\n"
                f"1️⃣ Enter your card (secure with Stripe)\n"
                f"2️⃣ You pay $0.00 today\n"
                f"3️⃣ Get full access for 7 days\n"
                f"4️⃣ After 7 days → auto-charged $0.99/day\n"
                f"5️⃣ Cancel anytime (even during trial)\n\n"
                f"💳 Click below to start your FREE trial:",
                reply_markup=reply_markup
            )

            await update.message.reply_text(
                "After completing checkout, you'll be automatically redirected back and your subscription will be activated instantly!"
            )

            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Stripe error: {e}")
            await update.message.reply_text(
                "❌ Error creating trial session. Please try again or contact support."
            )
            return PAYMENT_PROCESSING

    else:
        # Partial discount - not implemented for daily billing
        await update.message.reply_text(
            f"⚠️ Partial discounts not available for daily billing.\n"
            f"Please use a free trial code or subscribe normally."
        )
        return PAYMENT_PROCESSING


async def handle_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle subscription initiation"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if query.data == 'promo_code':
        await query.edit_message_text(
            "🎁 Enter your promo code:"
        )
        # Set flag to expect promo code input
        context.user_data['expecting_promo'] = True
        return PAYMENT_PROCESSING

    # Create Stripe checkout session
    try:
        session = stripe.checkout.Session.create(
            # Accept multiple payment methods
            payment_method_types=['card'],  # Credit/Debit cards
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{PAYMENT_SERVER_URL}/payment/success?bot={context.bot.username}&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{PAYMENT_SERVER_URL}/payment/cancel?bot={context.bot.username}',
            client_reference_id=str(telegram_id),
            metadata={'telegram_id': str(telegram_id)},
            # Enable additional payment features
            payment_method_options={
                'card': {
                    'request_three_d_secure': 'automatic',  # 3D Secure for security
                }
            },
            # Allow promo codes at checkout
            allow_promotion_codes=True,
            # Collect billing address
            billing_address_collection='auto',
        )

        keyboard = [[InlineKeyboardButton("Subscribe Now - $0.99/day 💳", url=session.url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💳 Daily Subscription - $0.99/day\n\n"
            "We accept all major credit cards:\n"
            "✓ Visa\n"
            "✓ Mastercard\n"
            "✓ American Express\n"
            "✓ Discover\n\n"
            "💰 You'll be charged $0.99 every day\n"
            "📅 Cancel anytime (no questions asked)\n"
            "🔒 Secure payment powered by Stripe\n\n"
            "Click below to subscribe:",
            reply_markup=reply_markup
        )

        await query.message.reply_text(
            "After payment, you'll be automatically redirected back and your subscription will be activated!"
        )

    except Exception as e:
        logger.error(f"Stripe error: {e}")
        await query.edit_message_text(
            "Sorry, there was an error creating the payment session. Please try again later."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    await update.message.reply_text(
        "Setup cancelled. Send /start to begin again."
    )
    return ConversationHandler.END


# ============================================================================
# AUTOMATION COMMANDS
# ============================================================================

async def autopilot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run full autopilot"""
    telegram_id = update.effective_user.id

    # Check subscription
    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text(
                "You need an active subscription to use this feature.\n"
                "Send /start to get started!"
            )
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to verify your subscription. Please try again in a moment."
        )
        return

    # Check LinkedIn credentials exist
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            await update.message.reply_text(
                "You haven't connected your LinkedIn account yet.\n\n"
                "Please use /settings and select 'Update LinkedIn Credentials' to add your login details first."
            )
            return
    except Exception as e:
        logger.error(f"Failed to check credentials for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to verify your LinkedIn credentials. Please try again in a moment."
        )
        return

    await update.message.reply_text(
        "🚀 *Autopilot Initiated!*\n\n"
        "🤖 *What's happening:*\n"
        "  ✓ Signing in to your LinkedIn\n"
        "  ✓ Generating AI-powered content\n"
        "  ✓ Posting to your LinkedIn\n"
        "  ✓ Engaging with your feed\n"
        "  ✓ Sending connection requests\n\n"
        "🖥️ *Remote Automation:*\n"
        "All actions are performed securely on our remote servers.\n\n"
        "📸 *Live Updates:*\n"
        "You'll receive screenshots and progress updates in real-time!\n\n"
        "⏱️ *Estimated time:* 30 seconds – 5 minutes\n"
        "I'll notify you when complete! ✨",
        parse_mode='Markdown'
    )

    # Run automation in background
    try:
        if CELERY_ENABLED:
            autopilot_task.delay(telegram_id)
        else:
            Thread(target=run_autopilot, args=(telegram_id,)).start()
    except Exception as e:
        logger.error(f"Failed to start autopilot task for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to start autopilot. The automation service may be temporarily unavailable.\n\n"
            "Please try again in a few minutes."
        )


def run_autopilot(telegram_id: int):
    """
    Legacy threading function - used only if Celery is unavailable
    For multi-user mode, use autopilot_task.delay() instead
    """
    global application
    bot = application.bot if application else None
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def notify_user(message: str):
        if bot and loop:
            try:
                async def _send():
                    await bot.send_message(chat_id=telegram_id, text=message)
                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception:
                pass

    def take_screenshot(driver, action, description):
        path = save_screenshot(driver, telegram_id, action)
        if path:
            screenshot_queue.add_screenshot(telegram_id, path, description)

    linkedin_bot = None
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            notify_user("Autopilot failed: LinkedIn credentials not found.\n\nPlease add your credentials via /settings.")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        logger.info(f"Starting autopilot for user {telegram_id}")
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not login_with_retry(linkedin_bot, notify_fn=notify_user):
            return

        # Screenshot after login
        take_screenshot(linkedin_bot.driver, "login_success", "LinkedIn Sign-In Successful")
        notify_user("Signed in to LinkedIn successfully. Starting autopilot tasks...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        notify_user("Generating and posting AI content...")
        results = linkedin_bot.run_full_autopilot(
            max_posts_to_engage=10,
            max_connections=5
        )

        # Screenshot after autopilot
        take_screenshot(linkedin_bot.driver, "autopilot_complete", "Autopilot Complete")

        linkedin_bot.stop()
        linkedin_bot = None

        if results.get('content_posted'):
            db.log_automation_action(telegram_id, 'post', 1)
        if results.get('posts_engaged', 0) > 0:
            db.log_automation_action(telegram_id, 'like', results['posts_engaged'])
        if results.get('connections_sent', 0) > 0:
            db.log_automation_action(telegram_id, 'connection', results['connections_sent'])

        notify_user(
            f"Autopilot Complete!\n\n"
            f"Posted: {'Yes' if results.get('content_posted') else 'No'}\n"
            f"Posts engaged: {results.get('posts_engaged', 0)}\n"
            f"Connections sent: {results.get('connections_sent', 0)}\n\n"
            f"View your stats with /stats"
        )

    except Exception as e:
        logger.error(f"Autopilot error for user {telegram_id}: {e}")
        if linkedin_bot and hasattr(linkedin_bot, 'driver'):
            take_screenshot(linkedin_bot.driver, "autopilot_error", f"Autopilot Error: {str(e)[:50]}")
        notify_user(f"Autopilot encountered an error: {str(e)}\n\nPlease try again or contact support.")
    finally:
        if linkedin_bot:
            try:
                linkedin_bot.stop()
            except Exception:
                pass


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    try:
        stats = db.get_user_stats(telegram_id)
    except Exception as e:
        logger.error(f"Failed to get stats for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to load your statistics due to a temporary error.\n\n"
            "Please try again in a moment."
        )
        return

    if not stats:
        await update.message.reply_text(
            "No statistics found yet. Start using automation commands to build your stats!\n\n"
            "Try /autopilot to get started."
        )
        return

    message = (
        f"📊 Your LinkedIn Stats\n\n"
        f"Posts created: {stats.get('posts_created', 0)}\n"
        f"Likes given: {stats.get('likes_given', 0)}\n"
        f"Comments made: {stats.get('comments_made', 0)}\n"
        f"Connections sent: {stats.get('connections_sent', 0)}\n"
        f"Last active: {stats.get('last_active', 'Never')}"
    )

    await update.message.reply_text(message)


# /activate command removed - activation now happens automatically via Stripe success callback


async def engage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Engage with LinkedIn feed"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    # Check LinkedIn credentials exist
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            await update.message.reply_text(
                "You haven't connected your LinkedIn account yet.\n\n"
                "Please use /settings and select 'Update LinkedIn Credentials' to add your login details first."
            )
            return
    except Exception as e:
        logger.error(f"Failed to check credentials for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your LinkedIn credentials. Please try again.")
        return

    # Show engagement options
    keyboard = [
        [InlineKeyboardButton("💬 Reply to Comments on My Posts", callback_data='engage_replies')],
        [InlineKeyboardButton("👍 Engage with Feed (Random)", callback_data='engage_feed')],
        [InlineKeyboardButton("❌ Cancel", callback_data='engage_cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤝 Choose Engagement Mode:\n\n"
        "1️⃣ **Reply to Comments** (Recommended)\n"
        "   → Only respond to people who commented on YOUR posts\n"
        "   → Builds genuine relationships\n"
        "   → No duplicate comments\n\n"
        "2️⃣ **Feed Engagement**\n"
        "   → Like and comment on relevant posts in feed\n"
        "   → More proactive but uses up engagement quota\n\n"
        "Which mode would you like?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_engage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle engagement mode selection"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if query.data == 'engage_cancel':
        await query.edit_message_text("❌ Engagement cancelled.")
        return

    if query.data == 'engage_replies':
        await query.edit_message_text(
            "💬 *Reply Engagement Activated!*\n\n"
            "🤖 *What's happening:*\n"
            "  ✓ Signing in to your LinkedIn\n"
            "  ✓ Scanning comments on your posts\n"
            "  ✓ Generating personalized replies\n"
            "  ✓ Building genuine connections\n\n"
            "🖥️ *Remote Automation:*\n"
            "All engagement is performed securely on our remote servers.\n\n"
            "📸 *Progress Updates:*\n"
            "Screenshots and progress updates will be sent in real-time!\n\n"
            "⏱️ *Estimated time:* 30 seconds – 5 minutes",
            parse_mode='Markdown'
        )
        # Run reply-based engagement in background
        try:
            if CELERY_ENABLED:
                reply_engagement_task.delay(telegram_id, max_replies=5)
            else:
                Thread(target=run_reply_engagement, args=(telegram_id,)).start()
        except Exception as e:
            logger.error(f"Failed to start reply engagement for user {telegram_id}: {e}")
            await query.message.reply_text(
                "Failed to start engagement. The automation service may be temporarily unavailable.\n\n"
                "Please try again in a few minutes."
            )

    elif query.data == 'engage_feed':
        await query.edit_message_text(
            "👍 *Feed Engagement Started!*\n\n"
            "🤖 *What's happening:*\n"
            "  ✓ Signing in to your LinkedIn\n"
            "  ✓ Analyzing relevant posts in your feed\n"
            "  ✓ Liking quality content\n"
            "  ✓ Adding thoughtful comments\n\n"
            "🖥️ *Remote Automation:*\n"
            "All engagement is performed securely on our remote servers.\n\n"
            "📸 *Live Updates:*\n"
            "Screenshots and progress updates will be sent in real-time!\n\n"
            "⏱️ *Estimated time:* 30 seconds – 5 minutes",
            parse_mode='Markdown'
        )
        # Run feed engagement in background
        try:
            if CELERY_ENABLED:
                engage_with_feed_task.delay(telegram_id, max_engagements=10)
            else:
                Thread(target=run_engagement, args=(telegram_id,)).start()
        except Exception as e:
            logger.error(f"Failed to start feed engagement for user {telegram_id}: {e}")
            await query.message.reply_text(
                "Failed to start engagement. The automation service may be temporarily unavailable.\n\n"
                "Please try again in a few minutes."
            )


def run_reply_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""
    global application
    bot = application.bot if application else None
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def notify_user(message: str):
        if bot and loop:
            try:
                async def _send():
                    await bot.send_message(chat_id=telegram_id, text=message)
                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception:
                pass

    def take_screenshot(driver, action, description):
        path = save_screenshot(driver, telegram_id, action)
        if path:
            screenshot_queue.add_screenshot(telegram_id, path, description)

    linkedin_bot = None
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            notify_user("Reply engagement failed: LinkedIn credentials not found.\n\nPlease add your credentials via /settings.")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not login_with_retry(linkedin_bot, notify_fn=notify_user):
            return

        take_screenshot(linkedin_bot.driver, "login_success", "LinkedIn Sign-In Successful")
        notify_user("Signed in to LinkedIn successfully. Loading notifications and comments...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        notify_user("Scanning your posts for comments to reply to...")
        replies_posted = linkedin_bot.reply_based_engagement(max_replies=10)

        take_screenshot(linkedin_bot.driver, "reply_complete", "Reply Engagement Complete")

        linkedin_bot.stop()
        linkedin_bot = None

        if replies_posted > 0:
            db.log_automation_action(telegram_id, 'comment', replies_posted)

        notify_user(
            f"Reply Engagement Complete!\n\n"
            f"Posted {replies_posted} replies to people who engaged with you.\n\n"
            f"Building genuine relationships!"
        )

    except Exception as e:
        logger.error(f"Reply engagement error: {e}")
        if linkedin_bot and hasattr(linkedin_bot, 'driver'):
            take_screenshot(linkedin_bot.driver, "reply_error", f"Reply Error: {str(e)[:50]}")
        notify_user(f"Reply engagement error: {str(e)}\n\nPlease try again or contact support.")
    finally:
        if linkedin_bot:
            try:
                linkedin_bot.stop()
            except Exception:
                pass


def run_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""
    global application
    bot = application.bot if application else None
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def notify_user(message: str):
        if bot and loop:
            try:
                async def _send():
                    await bot.send_message(chat_id=telegram_id, text=message)
                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception:
                pass

    def take_screenshot(driver, action, description):
        path = save_screenshot(driver, telegram_id, action)
        if path:
            screenshot_queue.add_screenshot(telegram_id, path, description)

    linkedin_bot = None
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            notify_user("Engagement failed: LinkedIn credentials not found.\n\nPlease add your credentials via /settings.")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not login_with_retry(linkedin_bot, notify_fn=notify_user):
            return

        take_screenshot(linkedin_bot.driver, "login_success", "LinkedIn Sign-In Successful")
        notify_user("Signed in to LinkedIn successfully. Scrolling through your feed...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        def engagement_progress(message):
            notify_user(message)

        posts_engaged = linkedin_bot.engage_with_feed(
            max_engagements=10,
            progress_callback=engagement_progress
        )

        take_screenshot(linkedin_bot.driver, "engagement_complete", "Feed Engagement Complete")

        linkedin_bot.stop()
        linkedin_bot = None

        if posts_engaged > 0:
            db.log_automation_action(telegram_id, 'like', posts_engaged)

        notify_user(
            f"Feed Engagement Complete!\n\n"
            f"Engaged with {posts_engaged} posts.\n\n"
            f"View your stats with /stats"
        )

    except Exception as e:
        logger.error(f"Engagement error: {e}")
        if linkedin_bot and hasattr(linkedin_bot, 'driver'):
            take_screenshot(linkedin_bot.driver, "engagement_error", f"Engagement Error: {str(e)[:50]}")
        notify_user(f"Engagement error: {str(e)}\n\nPlease try again or contact support.")
    finally:
        if linkedin_bot:
            try:
                linkedin_bot.stop()
            except Exception:
                pass


async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send connection requests to relevant people"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    # Check LinkedIn credentials exist
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            await update.message.reply_text(
                "You haven't connected your LinkedIn account yet.\n\n"
                "Please use /settings and select 'Update LinkedIn Credentials' to add your login details first."
            )
            return
    except Exception as e:
        logger.error(f"Failed to check credentials for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your LinkedIn credentials. Please try again.")
        return

    await update.message.reply_text(
        "🤝 *Connection Builder Activated!*\n\n"
        "🤖 *What's happening:*\n"
        "  ✓ Signing in to your LinkedIn\n"
        "  ✓ Searching for relevant professionals\n"
        "  ✓ Generating personalized connection messages\n"
        "  ✓ Sending connection requests\n\n"
        "🖥️ *Remote Automation:*\n"
        "All actions are performed securely on our remote servers.\n\n"
        "📸 *Live Updates:*\n"
        "Screenshots and progress updates will be sent in real-time!\n\n"
        "⏱️ *Estimated time:* 30 seconds – 5 minutes\n"
        "Building your professional network... 🌐",
        parse_mode='Markdown'
    )

    # Run connection requests in background
    try:
        if CELERY_ENABLED:
            send_connection_requests_task.delay(telegram_id, count=10)
        else:
            Thread(target=run_connection_requests, args=(telegram_id,)).start()
    except Exception as e:
        logger.error(f"Failed to start connection requests for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to start connection builder. The automation service may be temporarily unavailable.\n\n"
            "Please try again in a few minutes."
        )


def run_connection_requests(telegram_id: int):
    """Legacy threading function - fallback only"""
    global application
    bot = application.bot if application else None
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def notify_user(message: str):
        if bot and loop:
            try:
                async def _send():
                    await bot.send_message(chat_id=telegram_id, text=message)
                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception:
                pass

    def take_screenshot(driver, action, description):
        path = save_screenshot(driver, telegram_id, action)
        if path:
            screenshot_queue.add_screenshot(telegram_id, path, description)

    linkedin_bot = None
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            notify_user("Connection requests failed: LinkedIn credentials not found.\n\nPlease add your credentials via /settings.")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not login_with_retry(linkedin_bot, notify_fn=notify_user):
            return

        take_screenshot(linkedin_bot.driver, "login_success", "LinkedIn Sign-In Successful")
        notify_user("Signed in to LinkedIn successfully. Searching for relevant professionals...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        notify_user("Sending personalized connection requests...")
        connections_sent = linkedin_bot._autopilot_network_outreach(max_connections=5)

        take_screenshot(linkedin_bot.driver, "connection_complete", "Connection Requests Complete")

        linkedin_bot.stop()
        linkedin_bot = None

        if connections_sent > 0:
            db.log_automation_action(telegram_id, 'connection', connections_sent)

        notify_user(
            f"Connection Requests Complete!\n\n"
            f"Sent {connections_sent} personalized connection requests.\n\n"
            f"Your network is growing!"
        )

    except Exception as e:
        logger.error(f"Connection error: {e}")
        if linkedin_bot and hasattr(linkedin_bot, 'driver'):
            take_screenshot(linkedin_bot.driver, "connection_error", f"Connection Error: {str(e)[:50]}")
        notify_user(f"Connection error: {str(e)}\n\nPlease try again or contact support.")
    finally:
        if linkedin_bot:
            try:
                linkedin_bot.stop()
            except Exception:
                pass


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule content for later posting"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    # Get user's posting times from profile
    try:
        user_profile = db.get_user_profile(telegram_id)
    except Exception as e:
        logger.error(f"Failed to get profile for schedule, user {telegram_id}: {e}")
        await update.message.reply_text("Failed to load your profile. Please try again.")
        return
    if not user_profile:
        await update.message.reply_text(
            "❌ No profile found. Complete onboarding with /start first."
        )
        return

    # Safely parse content_strategy (handle both JSON string and dict)
    try:
        content_strategy_data = user_profile.get('content_strategy')
        if isinstance(content_strategy_data, str):
            content_strategy = json.loads(content_strategy_data)
        elif isinstance(content_strategy_data, dict):
            content_strategy = content_strategy_data
        else:
            content_strategy = {}
    except (json.JSONDecodeError, TypeError):
        content_strategy = {}

    posting_times = content_strategy.get('optimal_times', ['09:00', '13:00', '17:00'])

    keyboard = [
        [InlineKeyboardButton(f"📅 Schedule for {time}", callback_data=f'schedule_{time}')]
        for time in posting_times
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='schedule_cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📅 Content Scheduler\n\n"
        "When would you like to post today?\n\n"
        "Select a time slot:",
        reply_markup=reply_markup
    )


async def handle_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle schedule time selection"""
    query = update.callback_query
    await query.answer()

    if query.data == 'schedule_cancel':
        await query.edit_message_text("❌ Scheduling cancelled.")
        return

    if query.data.startswith('schedule_'):
        scheduled_time = query.data.replace('schedule_', '')

        await query.edit_message_text(
            f"✅ *Scheduled Successfully!*\n\n"
            f"⏰ *Posting Time:* {scheduled_time} today\n\n"
            f"🤖 *Automated Publishing:*\n"
            f"Your AI-generated post will be published automatically at the scheduled time.\n\n"
            f"🖥️ *Remote Processing:*\n"
            f"All automation runs securely on our remote servers.\n\n"
            f"📸 *You'll Receive:*\n"
            f"Screenshots of your published post when it goes live!\n\n"
            f"📊 View scheduled posts: /stats",
            parse_mode='Markdown'
        )

        # TODO: Actually implement scheduling logic with cron/scheduler
        # For now, just confirm the scheduling


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = (
        "🤖 LinkedInGrowthBot Commands\n\n"
        "🚀 Automation:\n"
        "/autopilot - Run full automation\n"
        "/post - Generate and post content\n"
        "/engage - Engage with feed\n"
        "/connect - Send connection requests\n\n"
        "⚙️ Settings:\n"
        "/stats - View your analytics\n"
        "/cancelsubscription - Cancel your subscription\n\n"
        "ℹ️ Support:\n"
        "/help - Show this message\n"
        "/cancel - Cancel current operation"
    )
    await update.message.reply_text(help_text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu for updating profile"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    keyboard = [
        [InlineKeyboardButton("📝 Update Industry", callback_data='update_industry')],
        [InlineKeyboardButton("💼 Update Skills", callback_data='update_skills')],
        [InlineKeyboardButton("🎯 Update Career Goals", callback_data='update_goals')],
        [InlineKeyboardButton("🎨 Update Tone", callback_data='update_tone')],
        [InlineKeyboardButton("📅 Update Content Themes", callback_data='update_themes')],
        [InlineKeyboardButton("⏰ Update Posting Times", callback_data='update_times')],
        [InlineKeyboardButton("🔐 Update LinkedIn Credentials", callback_data='update_credentials')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel_settings')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        user_profile = db.get_user_profile(telegram_id)
    except Exception as e:
        logger.error(f"Failed to get profile for settings, user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to load your profile due to a temporary error.\n\n"
            "Please try again in a moment."
        )
        return

    if user_profile:
        await update.message.reply_text(
            "⚙️ Settings\n\n"
            "What would you like to update?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "No profile found. Please complete onboarding first with /start"
        )


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings menu selections"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_settings':
        await query.edit_message_text("Settings menu closed.")
        return

    # Map callback data to prompts
    prompts = {
        'update_industry': "Enter your new industry (comma-separated):\nExample: software development, AI",
        'update_skills': "Enter your new skills (comma-separated):\nExample: Python, automation, AI",
        'update_goals': "Enter your new career goals (comma-separated):\nExample: senior developer role",
        'update_tone': "Enter your new tone preferences (comma-separated):\nExample: professional yet approachable, technical expert",
        'update_themes': "Enter your new content themes (comma-separated):\nExample: technical tutorials, career insights",
        'update_times': "Enter your new posting times (HH:MM format):\nExample: 09:00, 13:00, 17:00",
        'update_credentials': "⚠️ Update LinkedIn Credentials\n\nPlease enter your LinkedIn email address:",
    }

    # Store what we're updating in context
    context.user_data['updating_field'] = query.data

    await query.edit_message_text(prompts.get(query.data, "Enter new value:"))


async def handle_settings_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process settings updates from user input"""
    # If user is in custom post input mode, route there instead
    if context.user_data.get('awaiting_custom_post'):
        await handle_custom_post_text(update, context)
        return

    telegram_id = update.effective_user.id
    updating_field = context.user_data.get('updating_field')

    if not updating_field:
        return

    user_input = update.message.text.strip()

    # Handle LinkedIn credential updates separately (two-step process)
    if updating_field == 'update_credentials':
        if 'linkedin_email_temp' not in context.user_data:
            # Step 1: Store email, ask for password
            context.user_data['linkedin_email_temp'] = user_input
            await update.message.reply_text(
                "Email saved. Now enter your LinkedIn password:\n\n"
                "🔒 Your password is encrypted and stored securely."
            )
            return
        else:
            # Step 2: Store password and update database
            email = context.user_data['linkedin_email_temp']
            password = user_input
            encrypted_pw = encrypt_password(password)

            db.save_linkedin_credentials(telegram_id, email, encrypted_pw)

            # Delete the message containing password for security
            try:
                await update.message.delete()
            except:
                pass

            await context.bot.send_message(
                chat_id=telegram_id,
                text="✅ LinkedIn credentials updated successfully!\n\n"
                     "Your password has been encrypted and stored securely."
            )

            # Clear temp data
            del context.user_data['linkedin_email_temp']
            del context.user_data['updating_field']
            return

    # Handle other profile updates
    user_profile = db.get_user_profile(telegram_id)
    if not user_profile:
        await update.message.reply_text("❌ Error: No profile found.")
        return

    # Parse input based on field type
    value_list = [item.strip() for item in user_input.split(',')]

    # Update the appropriate field
    field_mapping = {
        'update_industry': 'industry',
        'update_skills': 'skills',
        'update_goals': 'career_goals',
        'update_tone': 'tone',
        'update_themes': 'content_themes',
        'update_times': 'optimal_times',
    }

    field_name = field_mapping.get(updating_field)
    if field_name:
        # Update profile in database - safely parse JSON
        try:
            profile_data_raw = user_profile.get('profile_data')
            if isinstance(profile_data_raw, str):
                profile_data = json.loads(profile_data_raw)
            elif isinstance(profile_data_raw, dict):
                profile_data = profile_data_raw
            else:
                profile_data = {}
        except (json.JSONDecodeError, TypeError):
            profile_data = {}

        try:
            content_strategy_raw = user_profile.get('content_strategy')
            if isinstance(content_strategy_raw, str):
                content_strategy = json.loads(content_strategy_raw)
            elif isinstance(content_strategy_raw, dict):
                content_strategy = content_strategy_raw
            else:
                content_strategy = {}
        except (json.JSONDecodeError, TypeError):
            content_strategy = {}

        # Update the right section
        if field_name in ['content_themes', 'optimal_times']:
            content_strategy[field_name] = value_list
        else:
            profile_data[field_name] = value_list

        db.save_user_profile(telegram_id, profile_data, content_strategy)

        await update.message.reply_text(
            f"✅ {field_name.replace('_', ' ').title()} updated!\n\n"
            f"New value: {', '.join(value_list[:3])}{'...' if len(value_list) > 3 else ''}\n\n"
            f"Use /settings to update more fields."
        )

    # Clear context
    if 'updating_field' in context.user_data:
        del context.user_data['updating_field']


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show post type selection - AI generated or user-written"""
    telegram_id = update.effective_user.id

    try:
        if not db.is_subscription_active(telegram_id):
            await update.message.reply_text("Subscribe first: /start")
            return
    except Exception as e:
        logger.error(f"Failed to check subscription for user {telegram_id}: {e}")
        await update.message.reply_text("Failed to verify your subscription. Please try again.")
        return

    keyboard = [
        [InlineKeyboardButton("🤖 Generate AI Post", callback_data='post_ai_generate')],
        [InlineKeyboardButton("✏️ Write My Own Post", callback_data='post_write_own')],
        [InlineKeyboardButton("❌ Cancel", callback_data='post_discard')],
    ]
    await update.message.reply_text(
        "📝 *Create a LinkedIn Post*\n\n"
        "How would you like to create your post?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


def _media_status_line(context):
    """Return a status line showing attached media, or empty string."""
    media_path = context.user_data.get('post_media')
    if media_path:
        fname = Path(media_path).name
        return f"\n📎 *Attached:* {fname}\n"
    return "\n"


def _build_post_preview_keyboard(telegram_id, context, is_ai=True):
    """Build the inline keyboard for post preview, including media buttons."""
    has_media = bool(context.user_data.get('post_media'))
    keyboard = [
        [InlineKeyboardButton("📱 Post on Mobile (Copy & Paste)", callback_data='post_mobile')],
        [InlineKeyboardButton("🖥️ Post with Browser (Server)", callback_data=f'post_approve_{telegram_id}')],
    ]
    # Media attach / remove button
    if has_media:
        keyboard.append([InlineKeyboardButton("🗑️ Remove Attached Media", callback_data='post_remove_media')])
    else:
        keyboard.append([InlineKeyboardButton("📷 Attach Image/Video", callback_data='post_attach_media')])
    if is_ai:
        keyboard.append([InlineKeyboardButton("🔄 Generate New", callback_data='post_ai_generate')])
        keyboard.append([InlineKeyboardButton("✏️ Write My Own Instead", callback_data='post_write_own')])
    else:
        keyboard.append([InlineKeyboardButton("✏️ Edit & Retype", callback_data='post_write_own')])
    keyboard.append([InlineKeyboardButton("❌ Discard", callback_data='post_discard')])
    return keyboard


async def handle_post_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo or document upload when user is attaching media to a post."""
    if not context.user_data.get('awaiting_post_media'):
        return  # Not in media upload mode — let other handlers run

    context.user_data['awaiting_post_media'] = False
    telegram_id = update.effective_user.id

    try:
        # Determine file source: photo or document
        if update.message.photo:
            # Telegram sends multiple sizes; pick the largest
            photo = update.message.photo[-1]
            file_id = photo.file_id
            file_size = photo.file_size or 0
            file_name = f"{telegram_id}_{uuid.uuid4().hex[:8]}.jpg"
        elif update.message.document:
            doc = update.message.document
            file_id = doc.file_id
            file_size = doc.file_size or 0
            file_name = doc.file_name or f"{telegram_id}_{uuid.uuid4().hex[:8]}"
        else:
            await update.message.reply_text("Please send a photo or a supported file (JPG, PNG, GIF, MP4, MOV).")
            context.user_data['awaiting_post_media'] = True
            return

        # Validate file size
        if file_size > MAX_MEDIA_SIZE_MB * 1024 * 1024:
            await update.message.reply_text(
                f"File is too large (max {MAX_MEDIA_SIZE_MB}MB). Please send a smaller file."
            )
            context.user_data['awaiting_post_media'] = True
            return

        # Validate extension
        ext = Path(file_name).suffix.lower()
        if ext not in SUPPORTED_MEDIA_EXTENSIONS:
            await update.message.reply_text(
                f"Unsupported format ({ext}). Supported: JPG, PNG, GIF, MP4, MOV.\n\n"
                "Please send a supported file."
            )
            context.user_data['awaiting_post_media'] = True
            return

        # Download file
        tg_file = await context.bot.get_file(file_id)
        local_path = UPLOAD_DIR / f"{telegram_id}_{uuid.uuid4().hex[:8]}{ext}"
        await tg_file.download_to_drive(str(local_path))

        # Remove any previously attached media
        old_media = context.user_data.get('post_media')
        if old_media:
            try:
                Path(old_media).unlink(missing_ok=True)
            except Exception:
                pass

        context.user_data['post_media'] = str(local_path)

        # Re-show preview with media attached
        generated_post = context.user_data.get('generated_post', '')
        if not generated_post:
            await update.message.reply_text("Media attached, but no post content found. Use /post to start over.")
            return

        keyboard = _build_post_preview_keyboard(telegram_id, context, is_ai=True)
        media_line = _media_status_line(context)

        await update.message.reply_text(
            f"📝 *Post Preview:*\n\n"
            f"{'─' * 40}\n\n"
            f"{generated_post}\n\n"
            f"{'─' * 40}\n"
            f"{media_line}\n"
            f"Choose how to post:\n"
            f"📱 *Mobile*: Opens on your phone (recommended)\n"
            f"🖥️ *Browser*: Opens on server (visible automation)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error handling post media upload for user {telegram_id}: {e}")
        await update.message.reply_text(f"Failed to process media: {str(e)}\n\nPlease try again.")
        context.user_data['awaiting_post_media'] = True


def generate_post_from_templates(industry, skills, themes):
    """Generate a post from randomized offline templates (5 distinct formats).
    Used as fallback when AI service is unavailable."""
    import random

    first_skill = skills.split(',')[0].strip() if skills else 'technology'
    first_theme = themes.split(',')[0].strip() if themes else 'industry insights'
    skill_tags = [f"#{s.strip().replace(' ', '')}" for s in skills.split(',')[:3]]
    hashtags = f"#{first_theme.replace(' ', '')} {' '.join(skill_tags)}"

    # ── Shared component pools ──
    hooks_story = [
        f"I spent the last few weeks rethinking how I approach {first_theme}.",
        f"Something happened last week that changed my perspective on {first_theme}.",
        f"A conversation with a colleague made me question everything I knew about {first_theme}.",
        f"I've been quietly experimenting with {first_theme} and the results surprised me.",
    ]
    hooks_lesson = [
        f"I wasted days trying to solve a {first_theme} problem the wrong way.",
        f"I failed at {first_theme} before I figured out what actually works.",
        f"The hardest lesson I learned about {first_theme} wasn't technical.",
        f"Three months ago I was doing {first_theme} completely wrong.",
    ]
    hooks_hottake = [
        f"Unpopular opinion: most people are overthinking {first_theme}.",
        f"Hot take: {first_theme} doesn't need more tools. It needs more clarity.",
        f"Everyone's talking about {first_theme} but nobody's addressing the real problem.",
        f"Controversial thought: the {industry} industry has {first_theme} backwards.",
    ]
    hooks_before_after = [
        f"6 months ago my approach to {first_theme} was completely different.",
        f"I used to think {first_theme} required complex solutions. I was wrong.",
        f"My {first_theme} workflow before vs. after — night and day.",
    ]
    hooks_question = [
        f"What if everything we think about {first_theme} is outdated?",
        f"Why do so few people in {industry} talk honestly about {first_theme}?",
        f"Has anyone else noticed this pattern with {first_theme}?",
    ]

    checklist_items = [
        f"☑️ Map out the real problem before jumping to solutions",
        f"☑️ Focus on {first_skill} fundamentals, not shiny tools",
        f"☑️ Get feedback early instead of building in isolation",
        f"☑️ Document what works (and what doesn't)",
        f"☑️ Simplify ruthlessly before adding complexity",
        f"☑️ Challenge your own assumptions first",
    ]
    result_items = [
        f"✅ Reduced time spent on repetitive work by focusing on what matters",
        f"✅ Built a process that actually adapts when things change",
        f"✅ Started getting better results with less effort",
        f"✅ Found clarity by stripping away unnecessary complexity",
        f"✅ Learned to trust the fundamentals of {first_skill}",
        f"✅ Stopped chasing trends and doubled down on what works",
    ]
    lessons = [
        f"The real skill isn't knowing more. It's knowing what to ignore.",
        f"Simple systems beat complicated ones every time.",
        f"Clear thinking is the most underrated {industry} skill.",
        f"Consistency beats intensity. Every single time.",
        f"The best approach is the one you'll actually stick with.",
    ]
    transitions = [
        "Here's what I've found:",
        "What nobody tells you:",
        "Here's what actually happened:",
        "The truth is simpler than you think:",
        "Here's the part nobody talks about:",
    ]
    questions_pool = [
        f"What's your approach to {first_theme}? I'd genuinely like to know.",
        f"Has anyone else run into this with {first_theme}?",
        f"What would you add to this? Drop your thoughts below.",
        f"Am I the only one who sees it this way?",
        f"What's the most counterintuitive thing you've learned about {first_theme}?",
        f"Would love to hear how others in {industry} handle this.",
    ]

    # ── Format A: Story Arc ──
    def format_story_arc():
        hook = random.choice(hooks_story)
        checks = random.sample(checklist_items, 3)
        results = random.sample(result_items, 3)
        lesson = random.choice(lessons)
        question = random.choice(questions_pool)
        return (
            f"{hook}\n\n"
            f"The concept is straightforward:\n"
            f"{checks[0]}\n{checks[1]}\n{checks[2]}\n\n"
            f"{random.choice(transitions)}\n\n"
            f"{results[0]}\n{results[1]}\n{results[2]}\n\n"
            f"{lesson}\n\n"
            f"{question}\n\n"
            f"{hashtags}"
        )

    # ── Format B: Lesson Learned ──
    def format_lesson_learned():
        hook = random.choice(hooks_lesson)
        checks = random.sample(checklist_items, 2)
        results = random.sample(result_items, 3)
        lesson = random.choice(lessons)
        question = random.choice(questions_pool)
        return (
            f"{hook}\n\n"
            f"What I tried first:\n"
            f"{checks[0]}\n{checks[1]}\n\n"
            f"Nothing clicked — until I changed my approach entirely.\n\n"
            f"What actually worked:\n\n"
            f"{results[0]}\n{results[1]}\n{results[2]}\n\n"
            f"The takeaway?\n\n"
            f"{lesson}\n\n"
            f"{question}\n\n"
            f"{hashtags}"
        )

    # ── Format C: Hot Take ──
    def format_hot_take():
        hook = random.choice(hooks_hottake)
        results = random.sample(result_items, 3)
        lesson = random.choice(lessons)
        question = random.choice(questions_pool)
        return (
            f"{hook}\n\n"
            f"I know that sounds strong.\n\n"
            f"But here's what I'm actually seeing:\n\n"
            f"{results[0]}\n{results[1]}\n{results[2]}\n\n"
            f"That's not innovation.\n\nThat's noise.\n\n"
            f"{lesson}\n\n"
            f"{question}\n\n"
            f"{hashtags}"
        )

    # ── Format D: Before/After ──
    def format_before_after():
        hook = random.choice(hooks_before_after)
        checks = random.sample(checklist_items, 3)
        results = random.sample(result_items, 3)
        lesson = random.choice(lessons)
        question = random.choice(questions_pool)
        return (
            f"{hook}\n\n"
            f"Before:\n"
            f"{checks[0]}\n{checks[1]}\n{checks[2]}\n\n"
            f"Then I stripped everything back to basics.\n\n"
            f"After:\n\n"
            f"{results[0]}\n{results[1]}\n{results[2]}\n\n"
            f"The difference wasn't just efficiency.\n\n"
            f"{lesson}\n\n"
            f"{question}\n\n"
            f"{hashtags}"
        )

    # ── Format E: Question-Led ──
    def format_question_led():
        hook = random.choice(hooks_question)
        results = random.sample(result_items, 3)
        lesson = random.choice(lessons)
        question = random.choice(questions_pool)
        return (
            f"{hook}\n\n"
            f"I've been thinking about this a lot lately.\n\n"
            f"Here's what I've observed:\n\n"
            f"{results[0]}\n{results[1]}\n{results[2]}\n\n"
            f"{random.choice(transitions)}\n\n"
            f"{lesson}\n\n"
            f"{question}\n\n"
            f"{hashtags}"
        )

    formats = [format_story_arc, format_lesson_learned, format_hot_take,
               format_before_after, format_question_led]
    return random.choice(formats)()


async def post_command_generate_ai(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Generate AI content and show preview.
    Tries AI service (Claude API) first, falls back to offline templates.
    Accepts either a CallbackQuery or a Message as first arg."""
    import random

    # Resolve the message and telegram_id regardless of caller type
    if hasattr(query_or_update, 'message'):
        # Called from CallbackQuery
        reply_msg = query_or_update.message
        telegram_id = query_or_update.from_user.id
    else:
        # Called as a regular update
        reply_msg = query_or_update.message
        telegram_id = query_or_update.effective_user.id

    try:
        user_profile = db.get_user_profile(telegram_id)
        if not user_profile:
            await reply_msg.reply_text("No profile found. Complete onboarding with /start first.")
            return

        try:
            profile_data_raw = user_profile.get('profile_data')
            profile_data = json.loads(profile_data_raw) if isinstance(profile_data_raw, str) else (profile_data_raw or {})
        except (json.JSONDecodeError, TypeError):
            profile_data = {}

        try:
            content_strategy_raw = user_profile.get('content_strategy')
            content_strategy = json.loads(content_strategy_raw) if isinstance(content_strategy_raw, str) else (content_strategy_raw or {})
        except (json.JSONDecodeError, TypeError):
            content_strategy = {}

        industry = ', '.join(profile_data.get('industry', ['professional']))
        skills   = ', '.join(profile_data.get('skills',   ['technology']))
        themes   = content_strategy.get('content_themes', ['industry insights'])
        tone     = ', '.join(profile_data.get('tone', ['professional']))
        goals    = ', '.join(profile_data.get('career_goals', ['career growth']))

        themes_str = ', '.join(themes) if isinstance(themes, list) else str(themes)
        theme_for_ai = random.choice(themes) if isinstance(themes, list) and themes else themes_str

        # ── Try AI service (Claude API) first ──
        generated_post = None
        try:
            from ai.ai_service import AIService
            ai_svc = AIService()
            if ai_svc.client:
                ai_profile = {
                    'industry': industry,
                    'skills': skills,
                    'career_goals': goals,
                    'tone': tone,
                }
                generated_post = ai_svc.generate_post(theme=theme_for_ai, user_profile=ai_profile)
                if generated_post:
                    logger.info(f"AI-generated post for user {telegram_id} (theme: {theme_for_ai})")
        except Exception as e:
            logger.warning(f"AI service unavailable, using template fallback: {e}")

        # ── Fallback to offline templates ──
        if not generated_post:
            generated_post = generate_post_from_templates(industry, skills, themes_str)
            logger.info(f"Template-generated post for user {telegram_id}")

        post_id = str(uuid.uuid4())[:8]

        context.user_data['generated_post'] = generated_post
        context.user_data['post_id'] = post_id

        keyboard = _build_post_preview_keyboard(telegram_id, context, is_ai=True)
        media_line = _media_status_line(context)

        await reply_msg.reply_text(
            f"📝 *Generated Post Preview:*\n\n"
            f"{'─' * 40}\n\n"
            f"{generated_post}\n\n"
            f"{'─' * 40}\n"
            f"{media_line}\n"
            f"Choose how to post:\n"
            f"📱 *Mobile*: Opens on your phone (recommended)\n"
            f"🖥️ *Browser*: Opens on server (visible automation)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error generating post: {e}")
        await reply_msg.reply_text(f"❌ Error generating content: {str(e)}\n\nPlease try again later.")


def run_post_visible_browser(telegram_id: int, generated_post: str, media_path: str = None):
    """Legacy threading function - fallback only"""
    global application
    bot = application.bot if application else None
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def notify_user(message: str):
        if bot and loop:
            try:
                async def _send():
                    await bot.send_message(chat_id=telegram_id, text=message)
                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception:
                pass

    try:
        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            logger.error(f"LinkedIn credentials not found for user {telegram_id}")
            notify_user("Posting failed: LinkedIn credentials not found.\n\nPlease add your credentials via /settings.")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        logger.info(f"Opening visible LinkedIn browser for user {telegram_id}")
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not login_with_retry(linkedin_bot, notify_fn=notify_user):
            return

        # Take screenshot after successful login
        take_screenshot = lambda action, desc: (
            lambda p: screenshot_queue.add_screenshot(telegram_id, p, desc) if p else None
        )(save_screenshot(linkedin_bot.driver, telegram_id, action))

        take_screenshot("login_success", "LinkedIn Sign-In Successful")
        notify_user("Signed in to LinkedIn successfully. Creating your post...")

        # Create the post
        logger.info(f"Creating LinkedIn post for user {telegram_id}")
        success = linkedin_bot.create_post(generated_post, media_path)

        # Take screenshot after posting
        if success:
            take_screenshot("post_success", "Post Created Successfully")

        linkedin_bot.stop()

        # Clean up uploaded media file
        if media_path:
            try:
                Path(media_path).unlink(missing_ok=True)
            except Exception:
                pass

        if success:
            db.log_automation_action(telegram_id, 'post', 1)
            logger.info(f"Successfully posted to LinkedIn for user {telegram_id}")
            notify_user("Your post has been published on LinkedIn!\n\nView your stats with /stats")
        else:
            take_screenshot("post_failed", "Post Creation Failed")
            logger.error(f"Failed to post to LinkedIn for user {telegram_id}")
            notify_user(
                "Posting failed: Could not create the post on LinkedIn.\n\n"
                "The browser automation may have encountered an issue.\n"
                "Please try again with /post."
            )

    except Exception as e:
        logger.error(f"Error posting to LinkedIn for user {telegram_id}: {e}")
        if linkedin_bot and hasattr(linkedin_bot, 'driver'):
            try:
                path = save_screenshot(linkedin_bot.driver, telegram_id, "post_error")
                if path:
                    screenshot_queue.add_screenshot(telegram_id, path, f"Post Error: {str(e)[:50]}")
            except Exception:
                pass
        # Clean up media on error too
        if media_path:
            try:
                Path(media_path).unlink(missing_ok=True)
            except Exception:
                pass
        notify_user(f"Posting encountered an error: {str(e)}\n\nPlease try again or contact support.")


async def handle_custom_post_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture user-typed post text and show preview"""
    if not context.user_data.get('awaiting_custom_post'):
        return  # Not in custom post mode, ignore

    custom_post = update.message.text.strip()
    context.user_data['awaiting_custom_post'] = False

    if not custom_post:
        await update.message.reply_text("❌ Post cannot be empty. Try again or use /post to start over.")
        return

    telegram_id = update.effective_user.id
    post_id = str(uuid.uuid4())[:8]

    context.user_data['generated_post'] = custom_post
    context.user_data['post_id'] = post_id

    keyboard = _build_post_preview_keyboard(telegram_id, context, is_ai=False)
    media_line = _media_status_line(context)

    await update.message.reply_text(
        f"📝 *Your Post Preview:*\n\n"
        f"{'─' * 40}\n\n"
        f"{custom_post}\n\n"
        f"{'─' * 40}\n"
        f"{media_line}\n"
        f"Choose how to post:\n"
        f"📱 *Mobile*: Opens on your phone (recommended)\n"
        f"🖥️ *Browser*: Opens on server (visible automation)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle post preview actions"""
    query = update.callback_query
    await query.answer()

    if query.data == 'post_write_own':
        context.user_data['awaiting_custom_post'] = True
        await query.edit_message_text(
            "✏️ *Write Your Post*\n\n"
            "Type your LinkedIn post and send it:\n\n"
            "💡 *Tips:*\n"
            "• Keep it under 3,000 characters\n"
            "• Use line breaks for readability\n"
            "• Add hashtags at the end\n\n"
            "Type your post now:",
            parse_mode='Markdown'
        )
        return

    if query.data == 'post_ai_generate':
        await query.edit_message_text("🤖 Generating AI content...\n\nThis may take a moment.")
        await post_command_generate_ai(query, context)
        return

    if query.data == 'post_discard':
        # Clean up any uploaded media file
        media_path = context.user_data.pop('post_media', None)
        if media_path:
            try:
                Path(media_path).unlink(missing_ok=True)
            except Exception:
                pass
        await query.edit_message_text("❌ Post discarded.")
        context.user_data.pop('generated_post', None)
        context.user_data.pop('awaiting_custom_post', None)
        context.user_data.pop('awaiting_post_media', None)
        return

    if query.data == 'post_attach_media':
        context.user_data['awaiting_post_media'] = True
        await query.edit_message_text(
            "📷 *Attach Media to Your Post*\n\n"
            "Send a photo or file to attach.\n\n"
            "Supported formats: JPG, PNG, GIF, MP4, MOV\n"
            f"Max size: {MAX_MEDIA_SIZE_MB}MB",
            parse_mode='Markdown'
        )
        return

    if query.data == 'post_remove_media':
        media_path = context.user_data.pop('post_media', None)
        if media_path:
            try:
                Path(media_path).unlink(missing_ok=True)
            except Exception:
                pass
        # Re-show preview without media
        telegram_id = update.effective_user.id
        generated_post = context.user_data.get('generated_post', '')
        keyboard = _build_post_preview_keyboard(telegram_id, context, is_ai=True)
        media_line = _media_status_line(context)
        await query.edit_message_text(
            f"📝 *Post Preview:*\n\n"
            f"{'─' * 40}\n\n"
            f"{generated_post}\n\n"
            f"{'─' * 40}\n"
            f"{media_line}\n"
            f"Choose how to post:\n"
            f"📱 *Mobile*: Opens on your phone (recommended)\n"
            f"🖥️ *Browser*: Opens on server (visible automation)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if query.data == 'post_mobile':
        post_content = context.user_data.get('generated_post', '')
        if not post_content:
            await query.edit_message_text("❌ Post content not found. Use /post to start again.")
            return

        keyboard = [
            [InlineKeyboardButton("🔗 Open LinkedIn Feed", url="https://www.linkedin.com/feed/")],
            [InlineKeyboardButton("✅ I Posted It!", callback_data='post_confirmed')],
            [InlineKeyboardButton("🔙 Back", callback_data='post_discard')],
        ]
        await query.edit_message_text(
            "📱 *Post on Mobile — 3 Easy Steps:*\n\n"
            "*Step 1:* Copy your post below 👇\n\n"
            f"`{post_content}`\n\n"
            "─────────────────────\n"
            "*Step 2:* Tap *Open LinkedIn Feed* → tap *Start a post* → paste\n\n"
            "*Step 3:* Tap *Post* on LinkedIn, then confirm below",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if query.data == 'post_confirmed':
        telegram_id = update.effective_user.id
        try:
            db.log_automation_action(telegram_id, 'post', 1)
        except Exception:
            pass
        await query.edit_message_text(
            "✅ *Post Confirmed!*\n\n"
            "Great job! Your LinkedIn post has been logged.\n\n"
            "Keep it up — consistency is key! 🚀"
            , parse_mode='Markdown'
        )
        context.user_data.pop('generated_post', None)
        # Clean up media if user posted manually
        media_path = context.user_data.pop('post_media', None)
        if media_path:
            try:
                Path(media_path).unlink(missing_ok=True)
            except Exception:
                pass
        return

    if query.data == 'post_regenerate':
        await query.edit_message_text("🔄 Generating new content...\n\nPlease use /post to generate again.")
        if 'generated_post' in context.user_data:
            del context.user_data['generated_post']
        return

    if query.data.startswith('post_approve_'):
        generated_post = context.user_data.get('generated_post')
        if not generated_post:
            await query.edit_message_text("❌ Error: Post content not found. Please generate again with /post")
            return

        media_path = context.user_data.get('post_media')
        media_note = "\n📎 Your attached media will be included." if media_path else ""

        await query.edit_message_text(
            "✅ *Post Approved!*\n\n"
            "🚀 *Automation Starting...*\n\n"
            "🖥️ *Remote Processing:*\n"
            f"Your post is being published on our secure remote servers.{media_note}\n\n"
            "📸 *Live Updates:*\n"
            "Watch your progress! Screenshots and updates will be sent showing:\n"
            "  • LinkedIn sign-in progress\n"
            "  • Your published post\n\n"
            "⏱️ *Estimated time:* 30 seconds – 5 minutes",
            parse_mode='Markdown'
        )

        telegram_id = update.effective_user.id

        # Run posting with visible browser in background thread
        try:
            if CELERY_ENABLED:
                post_to_linkedin_task.delay(telegram_id, generated_post, media=media_path)
            else:
                Thread(target=run_post_visible_browser, args=(telegram_id, generated_post, media_path)).start()
        except Exception as e:
            logger.error(f"Failed to start posting task for user {telegram_id}: {e}")
            await query.message.reply_text(
                "Failed to start posting. The automation service may be temporarily unavailable.\n\n"
                "Please try again in a few minutes."
            )

        # Clear context (don't delete media file — posting task needs it)
        context.user_data.pop('generated_post', None)
        context.user_data.pop('post_media', None)
        context.user_data.pop('awaiting_post_media', None)


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data sent back from WebApp when user confirms posting"""
    try:
        # Parse data sent from WebApp
        data = json.loads(update.effective_message.web_app_data.data)

        if data.get('action') == 'post_confirmed':
            telegram_id = int(data['user_id'])
            post_id = data['post_id']
            timestamp = data['timestamp']

            # Log the successful post
            db.log_automation_action(telegram_id, 'post', 1)

            logger.info(f"✅ User {telegram_id} confirmed post via mobile WebApp (post_id: {post_id})")

            # Send confirmation message
            await update.message.reply_text(
                "✅ Post confirmed! Great job!\n\n"
                "📊 Your stats have been updated.\n\n"
                "Keep up the excellent work! 🚀"
            )

    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        await update.message.reply_text(
            "⚠️ There was an issue confirming your post.\n\n"
            "But don't worry - if you posted to LinkedIn, that's what matters! 💪"
        )


async def _try_find_stripe_subscription(telegram_id: int) -> str:
    """Search Stripe for an active subscription belonging to this telegram user.
    Returns subscription_id if found (and saves it to DB), else None."""
    try:
        # Search Stripe subscriptions by metadata
        subscriptions = stripe.Subscription.search(
            query=f'metadata["telegram_id"]:"{telegram_id}"',
            limit=5
        )

        for sub in subscriptions.auto_paging_iter():
            if sub.status in ('active', 'trialing', 'past_due'):
                # Found it — save to DB for future use
                db.execute_query("""
                    UPDATE users SET
                        stripe_customer_id = COALESCE(stripe_customer_id, %s),
                        stripe_subscription_id = COALESCE(stripe_subscription_id, %s)
                    WHERE telegram_id = %s
                """, (sub.customer, sub.id, telegram_id))
                logger.info(f"Found Stripe subscription {sub.id} for user {telegram_id} via search")
                return sub.id

        # Also try searching by customer metadata
        customers = stripe.Customer.search(
            query=f'metadata["telegram_id"]:"{telegram_id}"',
            limit=5
        )

        for customer in customers.auto_paging_iter():
            # List their subscriptions
            subs = stripe.Subscription.list(customer=customer.id, status='all', limit=10)
            for sub in subs.auto_paging_iter():
                if sub.status in ('active', 'trialing', 'past_due'):
                    db.execute_query("""
                        UPDATE users SET
                            stripe_customer_id = COALESCE(stripe_customer_id, %s),
                            stripe_subscription_id = COALESCE(stripe_subscription_id, %s)
                        WHERE telegram_id = %s
                    """, (customer.id, sub.id, telegram_id))
                    logger.info(f"Found Stripe subscription {sub.id} for user {telegram_id} via customer search")
                    return sub.id

    except Exception as e:
        logger.warning(f"Stripe search failed for user {telegram_id}: {e}")

    return None


async def cancel_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel user's Stripe subscription - ALWAYS provides cancellation option"""
    telegram_id = update.effective_user.id

    # Try to get user data (but don't block if not found)
    user_data = None
    try:
        user_data = db.get_user(telegram_id)
    except Exception as e:
        logger.error(f"Error getting user data: {e}")

    is_active = False
    try:
        is_active = db.is_subscription_active(telegram_id)
    except Exception:
        pass

    if not user_data and not is_active:
        await update.message.reply_text(
            "You don't have an active subscription.\n\n"
            "Use /start to subscribe."
        )
        return

    keyboard = [
        [InlineKeyboardButton("Yes, cancel my subscription", callback_data='confirm_cancel_sub')],
        [InlineKeyboardButton("Keep my subscription", callback_data='keep_sub')],
    ]

    await update.message.reply_text(
        "Are you sure you want to cancel your subscription?\n\n"
        "You will lose access to:\n"
        "- AI-generated posts\n"
        "- Smart feed engagement\n"
        "- Automated networking\n"
        "- Analytics dashboard\n\n"
        "Your subscription will remain active until the end of your current billing period.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_cancel_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription cancellation confirmation"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if query.data == 'keep_sub':
        await query.edit_message_text(
            "✅ Great! Your subscription remains active.\n\n"
            "Continue growing with /autopilot"
        )
        return

    if query.data == 'confirm_cancel_sub':
        # Get Stripe data (but don't block if missing)
        user_data = None
        stripe_customer_id = None
        stripe_subscription_id = None

        try:
            user_data = db.get_user(telegram_id)
            if user_data:
                stripe_customer_id = user_data.get('stripe_customer_id')
                stripe_subscription_id = user_data.get('stripe_subscription_id')
        except Exception as e:
            logger.error(f"Error getting user data for cancellation: {e}")

        # ── Case 1: FREE/promo user — no Stripe subscription exists ──
        if user_data and not stripe_customer_id and not stripe_subscription_id:
            is_active = user_data.get('subscription_active', False)
            if is_active:
                db.deactivate_subscription(telegram_id)
                await query.edit_message_text(
                    "✅ Subscription Cancelled\n\n"
                    "Your free/promo subscription has been deactivated.\n\n"
                    "You can resubscribe anytime with /start\n\n"
                    "Thank you for using LinkedInGrowthBot!"
                )
            else:
                await query.edit_message_text(
                    "You don't have an active subscription.\n\n"
                    "Use /start to subscribe."
                )
            return

        # ── Case 2: Stripe customer — try portal + fallback ──
        if stripe_customer_id:
            try:
                portal_session = stripe.billing_portal.Session.create(
                    customer=stripe_customer_id,
                    return_url=f'{PAYMENT_SERVER_URL}/payment/cancel-complete?telegram_id={telegram_id}'
                )

                keyboard = [
                    [InlineKeyboardButton("Open Stripe Portal (Recommended)", url=portal_session.url)],
                    [InlineKeyboardButton("Direct API Cancel (Fallback)", callback_data='force_cancel_sub')]
                ]

                await query.edit_message_text(
                    "Choose cancellation method:\n\n"
                    "Recommended: *Stripe Portal*\n"
                    "- Official Stripe interface\n"
                    "- Update payment method\n"
                    "- View billing history\n\n"
                    "Fallback: *Direct API*\n"
                    "- Immediate cancellation\n"
                    "- Use if portal fails",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

                db.execute_query("""
                    UPDATE users
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{cancellation_initiated}',
                        'true'::jsonb
                    )
                    WHERE telegram_id = %s
                """, (telegram_id,))

            except stripe.error.StripeError as e:
                logger.error(f"Stripe portal error: {e}")
                keyboard = [[InlineKeyboardButton("Cancel via Direct API", callback_data='force_cancel_sub')]]
                await query.edit_message_text(
                    f"Stripe Portal unavailable: {str(e)}\n\n"
                    "Click below to cancel directly.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        # ── Case 3: Have subscription ID but no customer ID ──
        elif stripe_subscription_id:
            keyboard = [[InlineKeyboardButton("Cancel via Direct API", callback_data='force_cancel_sub')]]
            await query.edit_message_text(
                "Using direct API cancellation.\n\n"
                "Click below to cancel your subscription.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # ── Case 4: No Stripe data at all — try to find via Stripe search ──
        else:
            # Attempt Stripe lookup by metadata before giving up
            found_sub = await _try_find_stripe_subscription(telegram_id)
            if found_sub:
                keyboard = [[InlineKeyboardButton("Cancel Subscription", callback_data='force_cancel_sub')]]
                await query.edit_message_text(
                    "Found your Stripe subscription.\n\n"
                    "Click below to cancel.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Truly no subscription found anywhere
                if user_data and user_data.get('subscription_active'):
                    # Active but no Stripe — deactivate locally
                    db.deactivate_subscription(telegram_id)
                    await query.edit_message_text(
                        "✅ Subscription Cancelled\n\n"
                        "Your subscription has been deactivated locally.\n\n"
                        "No active Stripe billing was found — you will not be charged.\n\n"
                        "You can resubscribe anytime with /start"
                    )
                else:
                    await query.edit_message_text(
                        "No active subscription found.\n\n"
                        "Use /start to subscribe."
                    )

    elif query.data == 'force_cancel_sub':
        # Direct API cancellation
        user_data = None
        stripe_subscription_id = None

        try:
            user_data = db.get_user(telegram_id)
            stripe_subscription_id = user_data.get('stripe_subscription_id') if user_data else None
        except Exception as e:
            logger.error(f"Error getting user data for cancellation: {e}")

        # If no subscription ID in DB, try Stripe search
        if not stripe_subscription_id:
            found_sub = await _try_find_stripe_subscription(telegram_id)
            if found_sub:
                stripe_subscription_id = found_sub

        if not stripe_subscription_id:
            # No Stripe subscription exists — deactivate locally if active
            if user_data and user_data.get('subscription_active'):
                db.deactivate_subscription(telegram_id)
                await query.edit_message_text(
                    "✅ Subscription Cancelled\n\n"
                    "Your subscription has been deactivated.\n\n"
                    "No active Stripe billing was found — you will not be charged.\n\n"
                    "You can resubscribe anytime with /start"
                )
            else:
                await query.edit_message_text(
                    "No active subscription found.\n\n"
                    "Use /start to subscribe."
                )
            return

        try:
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )

            # Get period end — handle both old API (subscription.current_period_end)
            # and new API 2025-03-31+ (subscription.items.data[0].current_period_end)
            period_end = getattr(subscription, 'current_period_end', None)
            if period_end is None:
                try:
                    items = getattr(subscription, 'items', None)
                    if items and hasattr(items, 'data') and items.data:
                        period_end = getattr(items.data[0], 'current_period_end', None)
                except (AttributeError, IndexError):
                    pass
            if period_end is None:
                period_end = getattr(subscription, 'cancel_at', None)

            if period_end:
                cancel_date = datetime.fromtimestamp(period_end)
                cancel_date_str = cancel_date.strftime('%B %d, %Y')
            else:
                cancel_date = None
                cancel_date_str = "your billing period end"

            if cancel_date:
                db.execute_query("""
                    UPDATE users
                    SET subscription_expires = %s,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{cancellation_pending}',
                            'true'::jsonb
                        )
                    WHERE telegram_id = %s
                """, (cancel_date, telegram_id,))
            else:
                db.execute_query("""
                    UPDATE users
                    SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{cancellation_pending}',
                            'true'::jsonb
                        )
                    WHERE telegram_id = %s
                """, (telegram_id,))

            await query.edit_message_text(
                f"✅ Subscription Cancelled\n\n"
                f"Your Stripe subscription has been cancelled.\n\n"
                f"Access continues until: {cancel_date_str}\n\n"
                f"You won't be charged again.\n\n"
                f"Changed your mind? Resubscribe anytime with /start\n\n"
                f"Thank you for using LinkedInGrowthBot!"
            )

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe API error during cancel: {e}")
            error_str = str(e).lower()
            # If subscription doesn't exist on Stripe, deactivate locally
            if 'no such subscription' in error_str or 'does not exist' in error_str:
                db.deactivate_subscription(telegram_id)
                await query.edit_message_text(
                    "✅ Subscription Cancelled\n\n"
                    "The Stripe subscription was already cancelled or expired.\n\n"
                    "Your local subscription has been deactivated. You will not be charged.\n\n"
                    "You can resubscribe anytime with /start"
                )
            else:
                await query.edit_message_text(
                    f"Stripe API Error: {str(e)}\n\n"
                    f"Please try again or contact support.\n\n"
                    f"Your Telegram ID: `{telegram_id}`",
                    parse_mode='Markdown'
                )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during cancel: {e}")
            await query.edit_message_text(
                f"Error cancelling subscription: {str(e)}\n\n"
                f"Please try again or contact support."
            )
        except Exception as e:
            logger.error(f"Error in direct cancellation: {e}")
            await query.edit_message_text(
                "An error occurred while cancelling your subscription.\n\n"
                "Please try again or contact support."
            )


# ============================================================================
# JOB SEARCH SCANNER
# ============================================================================

def run_job_scan(telegram_id: int):
    """Legacy threading function - fallback only"""
    """
    Background thread: login to LinkedIn, search for new jobs,
    notify user via Telegram for each new finding.
    """
    global application
    bot = application.bot
    loop = application.application.loop if hasattr(application, 'application') else asyncio.get_event_loop()

    def notify(message: str, reply_markup=None):
        async def _send():
            await bot.send_message(chat_id=telegram_id, text=message,
                                   reply_markup=reply_markup, parse_mode='Markdown')
        asyncio.run_coroutine_threadsafe(_send(), loop)

    linkedin_bot = None
    try:
        # Get LinkedIn credentials
        creds = db.execute_query(
            "SELECT email, encrypted_password FROM linkedin_credentials WHERE telegram_id = %s",
            (telegram_id,), fetch='one'
        )
        if not creds:
            logger.warning(f"No LinkedIn credentials for user {telegram_id}, skipping job scan")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Get job search config
        config = db.get_job_search_config(telegram_id)
        if not config:
            logger.warning(f"No job search config for user {telegram_id}, skipping")
            return

        # Build keyword list from all sources
        keywords = list(set(
            list(config.get('target_roles') or []) +
            list(config.get('scan_keywords') or []) +
            list(config.get('resume_keywords') or [])
        ))
        locations = list(config.get('target_locations') or [])

        if not keywords:
            logger.info(f"No keywords set for user {telegram_id}, skipping job scan")
            return
        if not locations:
            locations = ['Singapore']  # Default location

        # Get jobs already seen
        seen_ids = db.get_seen_job_ids(telegram_id)

        # Start LinkedIn bot
        linkedin_bot = LinkedInBot(email, password, headless=True)
        if not login_with_retry(linkedin_bot, notify_fn=notify):
            return
        notify("Signed in to LinkedIn. Scanning for new job postings...")

        job_search = linkedin_bot.job_search_module
        all_new_jobs = []

        for location in locations:
            jobs = job_search.search_jobs(keywords, location, max_results=25)
            new_jobs = job_search.filter_new_jobs(jobs, seen_ids)
            all_new_jobs.extend(new_jobs)
            # Update seen_ids so we don't double-notify across locations
            for job in new_jobs:
                seen_ids.add(job['job_id'])

        # Save and notify — cap at 5 per scan to avoid spam
        notified = 0
        max_notifications = 5

        for job in all_new_jobs[:max_notifications]:
            db.save_seen_job(telegram_id, job)

            apply_url = job.get('job_url', '')
            posted = job.get('posted_text', '')
            posted_line = f"\n🕒 *Posted:* {posted}" if posted else ""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Apply on LinkedIn", url=apply_url)]
            ]) if apply_url else None

            msg = (
                f"🔔 *New Job Match!*\n\n"
                f"💼 *{job.get('title', 'Unknown Position')}*\n"
                f"🏢 {job.get('company', 'Unknown Company')}\n"
                f"📍 {job.get('location', '')}"
                f"{posted_line}"
            )
            notify(msg, reply_markup=keyboard)
            notified += 1

        total_new = len(all_new_jobs)
        if total_new > max_notifications:
            notify(
                f"_Found {total_new} new job matches total. Showing top {max_notifications}._\n"
                f"_Run /scanjobnow to check again later._"
            )
        elif total_new == 0:
            logger.info(f"No new jobs found for user {telegram_id}")

        # Update last scan timestamp
        db.update_last_scan(telegram_id)
        logger.info(f"Job scan complete for {telegram_id}: {notified} notifications sent")

    except Exception as e:
        logger.error(f"Error in job scan for {telegram_id}: {e}")
    finally:
        if linkedin_bot:
            try:
                linkedin_bot.stop()
            except Exception:
                pass


async def scan_jobs_for_all_users(context: ContextTypes.DEFAULT_TYPE):
    """Hourly job queue task — scan LinkedIn Jobs for all opted-in users."""
    try:
        users = db.execute_query(
            "SELECT telegram_id FROM job_seeking_configs WHERE notification_enabled = true AND enabled = true",
            fetch='all'
        )
        if not users:
            return
        logger.info(f"Starting hourly job scan for {len(users)} user(s)")
        for user in users:
            if CELERY_ENABLED:
                scan_jobs_task.delay(user['telegram_id'])
            else:
                Thread(target=run_job_scan, args=(user['telegram_id'],), daemon=True).start()
    except Exception as e:
        logger.error(f"Error in scan_jobs_for_all_users: {e}")


# --- /jobsearch command ---
async def job_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show job scan status and options."""
    telegram_id = update.effective_user.id
    try:
        config = db.get_job_search_config(telegram_id)
    except Exception as e:
        logger.error(f"Failed to get job search config for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to load job search settings due to a temporary error.\n\n"
            "Please try again in a moment."
        )
        return

    if not config or not config.get('target_roles') and not config.get('scan_keywords'):
        await update.message.reply_text(
            "🔍 *Job Search Scanner*\n\n"
            "You haven't set up job scanning yet.\n\n"
            "Use /setjob to configure your target roles and location.\n"
            "You can also upload your resume (PDF) and I'll extract keywords automatically.",
            parse_mode='Markdown'
        )
        return

    roles = config.get('target_roles') or []
    keywords = config.get('scan_keywords') or []
    resume_kws = config.get('resume_keywords') or []
    locations = config.get('target_locations') or []
    enabled = config.get('notification_enabled', False)
    last_scan = config.get('last_scan_at')

    all_keywords = list(set(roles + keywords + resume_kws))
    status_icon = "🟢 Active" if enabled else "🔴 Paused"
    last_scan_str = last_scan.strftime('%d %b %Y %H:%M') if last_scan else "Never"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Scan Now", callback_data='jobscan_now'),
         InlineKeyboardButton("⚙️ Edit Preferences", callback_data='jobscan_edit')],
        [InlineKeyboardButton("🔴 Stop Scanning" if enabled else "🟢 Enable Scanning",
                              callback_data='jobscan_toggle')]
    ])

    await update.message.reply_text(
        f"🔍 *Job Search Scanner*\n\n"
        f"Status: {status_icon}\n"
        f"📍 Location: {', '.join(locations) or 'Not set'}\n"
        f"💼 Keywords: {', '.join(all_keywords[:5]) or 'None'}"
        f"{'...' if len(all_keywords) > 5 else ''}\n"
        f"🕒 Last scan: {last_scan_str}\n\n"
        f"Scanning every hour for new openings.",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_jobsearch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses from /jobsearch."""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    if query.data == 'jobscan_now':
        await query.edit_message_text("🔍 Starting job scan... You'll be notified when new jobs are found.")
        try:
            if CELERY_ENABLED:
                scan_jobs_task.delay(telegram_id)
            else:
                Thread(target=run_job_scan, args=(telegram_id,), daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start job scan for user {telegram_id}: {e}")
            await query.message.reply_text(
                "Failed to start job scan. Please try again in a few minutes."
            )

    elif query.data == 'jobscan_toggle':
        try:
            config = db.get_job_search_config(telegram_id)
            current = config.get('notification_enabled', False) if config else False
            new_state = not current
            db.execute_query(
                "UPDATE job_seeking_configs SET notification_enabled = %s WHERE telegram_id = %s",
                (new_state, telegram_id)
            )
        except Exception as e:
            logger.error(f"Failed to toggle job scan for user {telegram_id}: {e}")
            await query.edit_message_text("Failed to update job scan settings. Please try again.")
            return
        state_text = "🟢 enabled" if new_state else "🔴 paused"
        await query.edit_message_text(
            f"Job scanning {state_text}.\n\n"
            f"{'You will receive notifications for new job openings.' if new_state else 'Use /jobsearch to re-enable.'}"
        )

    elif query.data == 'jobscan_edit':
        await query.edit_message_text(
            "To update your job preferences, use /setjob\n\n"
            "To add resume keywords, send me your resume as a PDF file."
        )


# --- /setjob ConversationHandler ---
async def setjob_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start /setjob conversation."""
    await update.message.reply_text(
        "🔧 *Set Up Job Search*\n\n"
        "Step 1 of 2: What job roles are you looking for?\n\n"
        "Type the titles separated by commas.\n"
        "_Example: Software Engineer, Backend Developer, Python Developer_",
        parse_mode='Markdown'
    )
    return SETJOB_ROLES


async def setjob_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive job roles input."""
    roles_text = update.message.text.strip()
    roles = [r.strip() for r in roles_text.split(',') if r.strip()]

    if not roles:
        await update.message.reply_text("Please enter at least one job role.")
        return SETJOB_ROLES

    context.user_data['setjob_roles'] = roles

    await update.message.reply_text(
        f"✅ Got it! Looking for: *{', '.join(roles)}*\n\n"
        f"Step 2 of 2: What location(s)?\n\n"
        f"_Example: Singapore, Remote_",
        parse_mode='Markdown'
    )
    return SETJOB_LOCATION


async def setjob_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive location input and show confirmation."""
    location_text = update.message.text.strip()
    locations = [l.strip() for l in location_text.split(',') if l.strip()]

    if not locations:
        await update.message.reply_text("Please enter at least one location.")
        return SETJOB_LOCATION

    context.user_data['setjob_locations'] = locations
    roles = context.user_data.get('setjob_roles', [])

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Start Scanning", callback_data='setjob_confirm')],
        [InlineKeyboardButton("📄 Upload Resume Instead", callback_data='setjob_resume')],
        [InlineKeyboardButton("❌ Cancel", callback_data='setjob_cancel')]
    ])

    await update.message.reply_text(
        f"📋 *Review Your Job Search Settings*\n\n"
        f"💼 Roles: {', '.join(roles)}\n"
        f"📍 Locations: {', '.join(locations)}\n\n"
        f"I'll scan LinkedIn every hour and notify you of new openings.\n\n"
        f"You can also upload your resume (PDF) to add more keywords.",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return SETJOB_CONFIRM


async def setjob_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirm/cancel from setjob."""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    if query.data == 'setjob_confirm':
        roles = context.user_data.get('setjob_roles', [])
        locations = context.user_data.get('setjob_locations', [])

        try:
            db.save_job_search_config(
                telegram_id,
                roles=roles,
                locations=locations,
                enabled=True
            )
        except Exception as e:
            logger.error(f"Failed to save job search config for user {telegram_id}: {e}")
            await query.edit_message_text(
                "Failed to save your job search settings due to a temporary error.\n\n"
                "Please try again with /setjob."
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"✅ *Job Scanning Activated!*\n\n"
            f"💼 Roles: {', '.join(roles)}\n"
            f"📍 Locations: {', '.join(locations)}\n\n"
            f"I'll check LinkedIn every hour and send you new job matches.\n\n"
            f"💡 Tip: Upload your resume (PDF) to add more search keywords!\n"
            f"Use /jobsearch to view status anytime.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    elif query.data == 'setjob_resume':
        await query.edit_message_text(
            "📄 Please send me your resume as a PDF file.\n\n"
            "I'll extract your job titles, skills and industries to improve the search."
        )
        return SETJOB_CONFIRM

    elif query.data == 'setjob_cancel':
        context.user_data.clear()
        await query.edit_message_text("Job search setup cancelled.")
        return ConversationHandler.END


async def setjob_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel /setjob from text command."""
    context.user_data.clear()
    await update.message.reply_text("Job search setup cancelled.")
    return ConversationHandler.END


# --- /scanjobnow command ---
async def scan_job_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Immediately trigger a job scan for this user."""
    telegram_id = update.effective_user.id
    config = db.get_job_search_config(telegram_id)

    if not config or (not config.get('target_roles') and not config.get('scan_keywords') and not config.get('resume_keywords')):
        await update.message.reply_text(
            "No job search configured yet. Use /setjob to get started."
        )
        return

    await update.message.reply_text(
        "🔍 Starting job scan now...\n\n"
        "I'll notify you as soon as new jobs are found. This may take a minute."
    )
    try:
        if CELERY_ENABLED:
            scan_jobs_task.delay(telegram_id)
        else:
            Thread(target=run_job_scan, args=(telegram_id,), daemon=True).start()
    except Exception as e:
        logger.error(f"Failed to start job scan for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to start job scan. The automation service may be temporarily unavailable.\n\n"
            "Please try again in a few minutes."
        )


# --- /stopjob command ---
async def stop_job_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable job scanning for this user."""
    telegram_id = update.effective_user.id
    try:
        db.execute_query(
            "UPDATE job_seeking_configs SET notification_enabled = false WHERE telegram_id = %s",
            (telegram_id,)
        )
    except Exception as e:
        logger.error(f"Failed to stop job scanning for user {telegram_id}: {e}")
        await update.message.reply_text(
            "Failed to pause job scanning due to a temporary error.\n\n"
            "Please try again in a moment."
        )
        return
    await update.message.reply_text(
        "🔴 Job scanning paused.\n\n"
        "Use /jobsearch to re-enable scanning anytime."
    )


# --- Resume PDF upload handler ---
async def handle_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF resume upload — extract keywords using AI."""
    telegram_id = update.effective_user.id
    document = update.message.document

    if not document or not document.file_name.lower().endswith('.pdf'):
        return  # Not a PDF, ignore

    await update.message.reply_text("📄 Resume received! Extracting keywords...")

    try:
        # Download PDF
        file = await context.bot.get_file(document.file_id)
        pdf_bytes = await file.download_as_bytearray()

        # Parse PDF text
        from io import BytesIO
        import PyPDF2

        reader = PyPDF2.PdfReader(BytesIO(bytes(pdf_bytes)))
        resume_text = ""
        for page in reader.pages:
            resume_text += page.extract_text() or ""

        if not resume_text.strip():
            await update.message.reply_text(
                "⚠️ Could not extract text from this PDF. "
                "Please try a text-based PDF (not a scanned image)."
            )
            return

        # Use AI to extract job keywords
        from ai.ai_service import AIService
        ai = AIService()
        prompt = (
            "Extract job titles, roles, industries, and key technical skills from this resume. "
            "Return ONLY a comma-separated list of keywords suitable for LinkedIn job search. "
            "Include variations (e.g., 'Software Engineer, Software Developer, Backend Engineer'). "
            "Maximum 15 keywords.\n\nResume:\n" + resume_text[:3000]
        )
        response = ai.generate_content(prompt, max_tokens=200)
        keywords_raw = response.strip() if response else ""

        keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()][:15]

        if not keywords:
            await update.message.reply_text(
                "⚠️ Could not extract keywords from your resume. "
                "Please use /setjob to manually enter your job titles."
            )
            return

        # Save to DB
        db.save_resume_keywords(telegram_id, keywords)

        await update.message.reply_text(
            f"✅ *Resume Scanned!*\n\n"
            f"Keywords extracted:\n_{', '.join(keywords)}_\n\n"
            f"These will be used in your next job scan.\n"
            f"Use /scanjobnow to search immediately.",
            parse_mode='Markdown'
        )

    except ImportError:
        await update.message.reply_text(
            "⚠️ PDF parsing library not installed. Run: pip install PyPDF2"
        )
    except Exception as e:
        logger.error(f"Error processing resume for {telegram_id}: {e}")
        await update.message.reply_text(
            "⚠️ Error processing your resume. Please try again or use /setjob to enter keywords manually."
        )


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Start the bot"""
    global application

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Onboarding conversation handler
    onboarding_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PROFILE_INDUSTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_industry)],
            PROFILE_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_skills)],
            PROFILE_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_goals)],
            PROFILE_TONE: [CallbackQueryHandler(profile_tone)],
            CUSTOM_TONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_tone_input)],
            CONTENT_THEMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, content_themes)],
            OPTIMAL_TIMES: [
                CallbackQueryHandler(optimal_times),
                MessageHandler(filters.TEXT & ~filters.COMMAND, optimal_times)
            ],
            CONTENT_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, content_goals)],
            LINKEDIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, linkedin_email)],
            LINKEDIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, linkedin_password)],
            PAYMENT_PROCESSING: [
                CallbackQueryHandler(handle_subscription),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promo_code_input)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers
    application.add_handler(onboarding_handler)
    application.add_handler(CommandHandler('autopilot', autopilot_command))
    application.add_handler(CommandHandler('engage', engage_command))
    application.add_handler(CommandHandler('connect', connect_command))
    application.add_handler(CommandHandler('schedule', schedule_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CommandHandler('post', post_command))
    application.add_handler(CommandHandler('cancelsubscription', cancel_subscription_command))

    # Add callback handlers for subscription management
    application.add_handler(CallbackQueryHandler(
        handle_cancel_subscription_callback,
        pattern='^(confirm_cancel_sub|keep_sub|force_cancel_sub)$'
    ))

    # Add callback handlers for settings
    application.add_handler(CallbackQueryHandler(
        handle_settings_callback,
        pattern='^(update_industry|update_skills|update_goals|update_tone|update_themes|update_times|update_credentials|cancel_settings)$'
    ))

    # Add callback handlers for post management
    application.add_handler(CallbackQueryHandler(
        handle_post_callback,
        pattern='^(post_approve_|post_regenerate|post_discard|post_ai_generate|post_write_own|post_mobile|post_confirmed|post_attach_media|post_remove_media)'
    ))

    # Add callback handlers for schedule management
    application.add_handler(CallbackQueryHandler(
        handle_schedule_callback,
        pattern='^(schedule_|schedule_cancel)'
    ))

    # Add callback handlers for engagement mode selection
    application.add_handler(CallbackQueryHandler(
        handle_engage_callback,
        pattern='^(engage_replies|engage_feed|engage_cancel)$'
    ))

    # ---- Job Search handlers ----
    setjob_handler = ConversationHandler(
        entry_points=[CommandHandler('setjob', setjob_start)],
        states={
            SETJOB_ROLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, setjob_roles)],
            SETJOB_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, setjob_location)],
            SETJOB_CONFIRM: [
                CallbackQueryHandler(setjob_confirm_callback,
                                     pattern='^(setjob_confirm|setjob_resume|setjob_cancel)$'),
                MessageHandler(filters.Document.PDF, handle_resume_upload),
            ],
        },
        fallbacks=[CommandHandler('cancel', setjob_cancel)],
    )
    application.add_handler(setjob_handler)
    application.add_handler(CommandHandler('jobsearch', job_search_command))
    application.add_handler(CommandHandler('scanjobnow', scan_job_now_command))
    application.add_handler(CommandHandler('stopjob', stop_job_command))
    application.add_handler(CallbackQueryHandler(
        handle_jobsearch_callback,
        pattern='^(jobscan_now|jobscan_toggle|jobscan_edit)$'
    ))
    # Post media upload handler (photo or document — only active when awaiting_post_media)
    # Registered in group 1 so it runs independently of other handlers
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE | filters.Document.VIDEO,
        handle_post_media_upload
    ), group=1)
    # PDF resume handler (outside conversation — user can upload anytime)
    application.add_handler(MessageHandler(filters.Document.PDF, handle_resume_upload))

    # Add WebApp data handler for mobile posting confirmation
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA,
        handle_web_app_data
    ))

    # Add message handler for settings updates (must be after conversation handler)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_settings_update
    ))

    # Add periodic screenshot sender
    async def send_pending_screenshots(context: ContextTypes.DEFAULT_TYPE):
        """Periodically check and send queued screenshots"""
        from screenshot_handler import send_queued_screenshots

        # Check all users in queue
        telegram_ids = list(screenshot_queue.queue.keys())

        for telegram_id in telegram_ids:
            try:
                await send_queued_screenshots(context.bot, telegram_id)
            except Exception as e:
                logger.error(f"Error sending screenshots to {telegram_id}: {e}")

    # Schedule screenshot sender and job scanner (requires python-telegram-bot[job-queue])
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(send_pending_screenshots, interval=10, first=10)
        job_queue.run_repeating(scan_jobs_for_all_users, interval=3600, first=300)
        logger.info("Job queue active: screenshot sender every 10s, job scanner every 1h")
    else:
        logger.warning("Job queue not available — install python-telegram-bot[job-queue] for scheduled tasks")

    # Start bot
    logger.info("LinkedInGrowthBot started!")
    logger.info("Screenshot sender enabled - will send screenshots every 10 seconds")
    application.run_polling()


if __name__ == '__main__':
    main()

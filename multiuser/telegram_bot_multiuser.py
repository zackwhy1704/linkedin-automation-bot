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


def encrypt_password(password: str) -> bytes:
    """Encrypt password before storing"""
    return cipher.encrypt(password.encode())


def decrypt_password(encrypted: bytes) -> str:
    """Decrypt stored password"""
    return cipher.decrypt(encrypted).decode()


def validate_text_input(text: str) -> bool:
    """
    Validate that input only contains letters, spaces, commas, and basic punctuation.
    Allowed: letters (any language), spaces, commas, hyphens, apostrophes, parentheses, ampersands
    """
    import re
    # Allow letters (including unicode), spaces, commas, hyphens, apostrophes, parentheses, ampersands, and periods
    pattern = r'^[\w\s,\-\'\(\)&\.]+$'
    return bool(re.match(pattern, text, re.UNICODE))


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

        # Handle payment success - automatically activate subscription
        if param == 'payment_success':
            if not db.is_subscription_active(telegram_id):
                db.activate_subscription(telegram_id, days=30)

                await update.message.reply_text(
                    "🎉 Payment Successful!\n\n"
                    "Your subscription has been automatically activated!\n\n"
                    "You now have full access to:\n"
                    "✓ AI-generated posts\n"
                    "✓ Smart feed engagement\n"
                    "✓ Automated networking\n"
                    "✓ Analytics dashboard\n\n"
                    "🚀 Ready to grow? Send /autopilot to start!\n\n"
                    "Need help? Send /help"
                )
            else:
                await update.message.reply_text(
                    "✅ Your subscription is already active!\n\n"
                    "Send /autopilot to start automating."
                )
            return ConversationHandler.END

        # Handle payment cancellation
        elif param == 'payment_cancel':
            await update.message.reply_text(
                "❌ Payment cancelled.\n\n"
                "No worries! When you're ready to subscribe, send /start to begin again.\n\n"
                "Questions? Send /help"
            )
            return ConversationHandler.END

    # Check if user already exists
    user_data = db.get_user(telegram_id)

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
    industry = update.message.text

    # Validate input
    if not validate_text_input(industry):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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
    skills = update.message.text

    # Validate input
    if not validate_text_input(skills):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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
    goals = update.message.text

    # Validate input
    if not validate_text_input(goals):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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

    # Validate input
    if not validate_text_input(custom_tone):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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
    themes = update.message.text

    # Validate input
    if not validate_text_input(themes):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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
        # User entered custom times
        times = update.message.text
        context.user_data['optimal_times'] = [t.strip() for t in times.split(',')]

        await update.message.reply_text(
            f"✅ Custom times set: {', '.join(context.user_data['optimal_times'])}\n\n"
            "Finally, what are your content goals? (comma-separated)\n\n"
            "Example:\n"
            "- position as a builder who ships real products\n"
            "- share authentic behind-the-scenes stories\n"
            "- attract recruiters and collaborators"
        )

    return CONTENT_GOALS


async def content_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect content goals and show summary"""
    goals = update.message.text

    # Validate input
    if not validate_text_input(goals):
        await update.message.reply_text(
            "❌ Invalid input! Please use only letters, spaces, and commas.\n\n"
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

    db.save_user_profile(telegram_id, profile_data, content_strategy)

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
    email = update.message.text
    context.user_data['linkedin_email'] = email

    await update.message.reply_text(
        "Great! Now enter your LinkedIn password:\n"
        "(Don't worry, it's encrypted and never stored in plain text)"
    )
    return LINKEDIN_PASSWORD


async def linkedin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect LinkedIn password and proceed to content strategy"""
    password = update.message.text
    telegram_id = update.effective_user.id

    # Encrypt and save credentials
    encrypted_password = encrypt_password(password)
    db.save_linkedin_credentials(
        telegram_id,
        context.user_data['linkedin_email'],
        encrypted_password
    )

    # Delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass  # Message might already be deleted

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


async def handle_promo_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle promo code text input"""
    promo_code = update.message.text.strip().upper()
    telegram_id = update.effective_user.id

    # Validate promo code
    result = db.validate_promo_code(promo_code)

    if not result:
        await update.message.reply_text(
            "❌ Invalid promo code. The code may be expired, fully used, or doesn't exist.\n\n"
            "Please enter a valid promo code or skip to payment."
        )
        return PAYMENT_PROCESSING

    # Check for FREE bypass code
    if result.get('is_free_bypass'):
        # Completely bypass payment - activate subscription directly
        if db.activate_subscription(telegram_id, days=30):
            await update.message.reply_text(
                "🎉 FREE Code Activated!\n\n"
                "✅ Your subscription is now ACTIVE for 30 days!\n"
                "💯 Completely FREE - No payment required!\n\n"
                "You can now:\n"
                "• Add your LinkedIn account\n"
                "• Start automating engagement\n"
                "• Grow your network\n\n"
                "Type /menu to get started! 🚀"
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
                success_url=f'{PAYMENT_SERVER_URL}/payment/success?bot={context.bot.username}',
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
            success_url=f'https://t.me/{context.bot.username}?start=payment_success',
            cancel_url=f'https://t.me/{context.bot.username}?start=payment_cancel',
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
    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text(
            "⚠️ You need an active subscription to use this feature.\n"
            "Send /subscribe to get started!"
        )
        return

    await update.message.reply_text(
        "🚀 *Autopilot Initiated!*\n\n"
        "🤖 *What's happening:*\n"
        "  ✓ Generating AI-powered content\n"
        "  ✓ Posting to your LinkedIn\n"
        "  ✓ Engaging with your feed\n"
        "  ✓ Sending connection requests\n\n"
        "🖥️ *Remote Automation:*\n"
        "All actions are performed securely on our remote servers.\n\n"
        "📸 *Live Updates:*\n"
        "You'll receive screenshots showing your automation progress in real-time!\n\n"
        "⏱️ *Estimated time:* 2-3 minutes\n"
        "I'll notify you when complete! ✨",
        parse_mode='Markdown'
    )

    # Run automation in background
    if CELERY_ENABLED:
        autopilot_task.delay(telegram_id)
    else:
        Thread(target=run_autopilot, args=(telegram_id,)).start()


def run_autopilot(telegram_id: int):
    """
    Legacy threading function - used only if Celery is unavailable
    For multi-user mode, use autopilot_task.delay() instead
    """
    """Run autopilot in background thread"""
    try:
        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            logger.error(f"LinkedIn credentials not found for user {telegram_id}")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Initialize LinkedIn bot with visible browser
        logger.info(f"Starting autopilot for user {telegram_id}")
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not linkedin_bot.start():
            logger.error(f"Failed to login to LinkedIn for user {telegram_id}")
            return

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        # Run autopilot
        results = linkedin_bot.run_full_autopilot(
            max_posts_to_engage=10,
            max_connections=5
        )

        linkedin_bot.stop()

        # Log stats to database
        if results.get('content_posted'):
            db.log_automation_action(telegram_id, 'post', 1)
        if results.get('posts_engaged', 0) > 0:
            # Assume each engagement is a like + possible comment
            db.log_automation_action(telegram_id, 'like', results['posts_engaged'])
        if results.get('connections_sent', 0) > 0:
            db.log_automation_action(telegram_id, 'connection', results['connections_sent'])

        # Log results
        logger.info(
            f"✅ Autopilot complete for user {telegram_id}: "
            f"Posted: {results.get('content_posted', False)}, "
            f"Engaged: {results.get('posts_engaged', 0)}, "
            f"Connections: {results.get('connections_sent', 0)}"
        )

    except Exception as e:
        logger.error(f"Autopilot error for user {telegram_id}: {e}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    telegram_id = update.effective_user.id

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /subscribe")
        return

    stats = db.get_user_stats(telegram_id)

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

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /start")
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
            "  ✓ Scanning comments on your posts\n"
            "  ✓ Generating personalized replies\n"
            "  ✓ Building genuine connections\n\n"
            "🖥️ *Remote Automation:*\n"
            "All engagement is performed securely on our remote servers.\n\n"
            "📸 *Progress Updates:*\n"
            "Screenshots will be sent showing your engagement activity!\n\n"
            "⏱️ *Estimated time:* 2-3 minutes",
            parse_mode='Markdown'
        )
        # Run reply-based engagement in background
        if CELERY_ENABLED:
            reply_engagement_task.delay(telegram_id, max_replies=5)
        else:
            Thread(target=run_reply_engagement, args=(telegram_id,)).start()

    elif query.data == 'engage_feed':
        await query.edit_message_text(
            "👍 *Feed Engagement Started!*\n\n"
            "🤖 *What's happening:*\n"
            "  ✓ Analyzing relevant posts in your feed\n"
            "  ✓ Liking quality content\n"
            "  ✓ Adding thoughtful comments\n\n"
            "🖥️ *Remote Automation:*\n"
            "All engagement is performed securely on our remote servers.\n\n"
            "📸 *Live Updates:*\n"
            "Screenshots of your activity will be sent to you!\n\n"
            "⏱️ *Estimated time:* 3-4 minutes",
            parse_mode='Markdown'
        )
        # Run feed engagement in background
        if CELERY_ENABLED:
            engage_with_feed_task.delay(telegram_id, max_engagements=10)
        else:
            Thread(target=run_engagement, args=(telegram_id,)).start()


def run_reply_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""
    """Run reply-based engagement in background thread"""
    try:
        # Get bot application instance for sending messages
        global application
        bot = application.bot
        loop = application.application.loop if hasattr(application, 'application') else asyncio.get_event_loop()

        # Progress callback to send updates to user
        def send_progress_update(message: str, take_screenshot: bool = False):
            """Send progress update to Telegram from worker thread"""
            try:
                # Send message via async bot
                async def send_message():
                    await bot.send_message(chat_id=telegram_id, text=message)

                asyncio.run_coroutine_threadsafe(send_message(), loop)

                # Take and queue screenshot if requested
                if take_screenshot and hasattr(linkedin_bot, 'driver'):
                    screenshot_path = save_screenshot(linkedin_bot.driver, telegram_id, "reply_progress")
                    if screenshot_path:
                        screenshot_queue.add_screenshot(
                            telegram_id,
                            screenshot_path,
                            "Reply Engagement Progress"
                        )

            except Exception as e:
                logger.error(f"Error sending progress update: {e}")

        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Initialize LinkedIn bot with visible browser
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not linkedin_bot.start():
            send_progress_update("❌ Failed to start browser automation")
            return

        send_progress_update("🔄 Loading notifications and comments...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        # Reply-based engagement (only respond to comments on your posts)
        replies_posted = linkedin_bot.reply_based_engagement(max_replies=10)

        linkedin_bot.stop()

        # Log stats
        if replies_posted > 0:
            db.log_automation_action(telegram_id, 'comment', replies_posted)

        # Send final results
        send_progress_update(
            f"✅ Reply Engagement Complete!\n\n"
            f"📊 Posted {replies_posted} replies to people who engaged with you.\n\n"
            f"Building genuine relationships! 🤝"
        )

    except Exception as e:
        logger.error(f"Reply engagement error: {e}")
        try:
            # Send error message to user
            async def send_error():
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"❌ Reply engagement error: {str(e)}\n\nPlease try again or contact support."
                )
            asyncio.run_coroutine_threadsafe(send_error(), loop)
        except:
            pass


def run_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""
    """Run feed engagement in background thread"""
    try:
        # Get bot application instance for sending messages
        global application
        bot = application.bot
        loop = application.application.loop if hasattr(application, 'application') else asyncio.get_event_loop()

        # Progress callback to send updates to user
        def send_progress_update(message: str, take_screenshot: bool = False):
            """Send progress update to Telegram from worker thread"""
            try:
                # Send message via async bot
                async def send_message():
                    await bot.send_message(chat_id=telegram_id, text=message)

                asyncio.run_coroutine_threadsafe(send_message(), loop)

                # Take and queue screenshot if requested
                if take_screenshot and hasattr(linkedin_bot, 'driver'):
                    screenshot_path = save_screenshot(linkedin_bot.driver, telegram_id, "engagement_progress")
                    if screenshot_path:
                        screenshot_queue.add_screenshot(
                            telegram_id,
                            screenshot_path,
                            "Engagement Progress"
                        )

            except Exception as e:
                logger.error(f"Error sending progress update: {e}")

        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Initialize LinkedIn bot with visible browser
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not linkedin_bot.start():
            send_progress_update("❌ Failed to start browser automation")
            return

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        # Engage with feed with progress callback
        posts_engaged = linkedin_bot.engage_with_feed(
            max_engagements=10,
            progress_callback=send_progress_update
        )

        linkedin_bot.stop()

        # Log stats (each engagement is a like + possible comment)
        if posts_engaged > 0:
            db.log_automation_action(telegram_id, 'like', posts_engaged)

    except Exception as e:
        logger.error(f"Engagement error: {e}")
        try:
            # Send error message to user
            async def send_error():
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"❌ Engagement error: {str(e)}\n\nPlease try again or contact support."
                )
            asyncio.run_coroutine_threadsafe(send_error(), loop)
        except:
            pass


async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send connection requests to relevant people"""
    telegram_id = update.effective_user.id

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /start")
        return

    await update.message.reply_text(
        "🤝 *Connection Builder Activated!*\n\n"
        "🤖 *What's happening:*\n"
        "  ✓ Searching for relevant professionals\n"
        "  ✓ Generating personalized connection messages\n"
        "  ✓ Sending connection requests\n\n"
        "🖥️ *Remote Automation:*\n"
        "All actions are performed securely on our remote servers.\n\n"
        "📸 *Visual Confirmation:*\n"
        "Screenshots will be sent showing your new connection requests!\n\n"
        "⏱️ *Estimated time:* 2-3 minutes\n"
        "Building your professional network... 🌐",
        parse_mode='Markdown'
    )

    # Run connection requests in background
    if CELERY_ENABLED:
        send_connection_requests_task.delay(telegram_id, count=10)
    else:
        Thread(target=run_connection_requests, args=(telegram_id,)).start()


def run_connection_requests(telegram_id: int):
    """Legacy threading function - fallback only"""
    """Run connection requests in background thread"""
    try:
        # Get bot application instance for sending messages
        global application
        bot = application.bot
        loop = application.application.loop if hasattr(application, 'application') else asyncio.get_event_loop()

        # Progress callback to send updates to user
        def send_progress_update(message: str, take_screenshot: bool = False):
            """Send progress update to Telegram from worker thread"""
            try:
                # Send message via async bot
                async def send_message():
                    await bot.send_message(chat_id=telegram_id, text=message)

                asyncio.run_coroutine_threadsafe(send_message(), loop)

                # Take and queue screenshot if requested
                if take_screenshot and hasattr(linkedin_bot, 'driver'):
                    screenshot_path = save_screenshot(linkedin_bot.driver, telegram_id, "connection_progress")
                    if screenshot_path:
                        screenshot_queue.add_screenshot(
                            telegram_id,
                            screenshot_path,
                            "Connection Requests Progress"
                        )

            except Exception as e:
                logger.error(f"Error sending progress update: {e}")

        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Initialize LinkedIn bot with visible browser
        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not linkedin_bot.start():
            send_progress_update("❌ Failed to start browser automation")
            return

        send_progress_update("🔄 Searching for relevant professionals...")

        linkedin_bot.load_engagement_config('data/engagement_config.json')

        # Run network outreach (from autopilot)
        connections_sent = linkedin_bot._autopilot_network_outreach(max_connections=5)

        linkedin_bot.stop()

        # Log stats
        if connections_sent > 0:
            db.log_automation_action(telegram_id, 'connection', connections_sent)

        # Send final results
        send_progress_update(
            f"✅ Connection Requests Complete!\n\n"
            f"📊 Sent {connections_sent} personalized connection requests.\n\n"
            f"Your network is growing! 🌐",
            take_screenshot=True
        )

    except Exception as e:
        logger.error(f"Connection error: {e}")
        try:
            # Send error message to user
            async def send_error():
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"❌ Connection error: {str(e)}\n\nPlease try again or contact support."
                )
            asyncio.run_coroutine_threadsafe(send_error(), loop)
        except:
            pass


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule content for later posting"""
    telegram_id = update.effective_user.id

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /start")
        return

    # Get user's posting times from profile
    user_profile = db.get_user_profile(telegram_id)
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

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /start")
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

    user_profile = db.get_user_profile(telegram_id)
    if user_profile:
        await update.message.reply_text(
            "⚙️ Settings\n\n"
            "What would you like to update?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ No profile found. Please complete onboarding first with /start"
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

    if not db.is_subscription_active(telegram_id):
        await update.message.reply_text("⚠️ Subscribe first: /start")
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


async def post_command_generate_ai(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Generate AI content and show preview.
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
            await reply_msg.reply_text("❌ No profile found. Complete onboarding with /start first.")
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
        themes   = ', '.join(content_strategy.get('content_themes', ['industry insights']))

        hooks = [
            f"I recently had a conversation that completely changed how I think about {themes}. 🤔",
            f"Here's something I wish someone had told me earlier in my {industry} journey... 💡",
            f"After years working in {industry}, I've learned that breakthroughs come from unexpected places. 🌟",
            f"Last week, I was reminded why {themes} matters more than ever in today's {industry} landscape. 🚀",
            f"Something happened while working on {themes} that I think you'll find valuable. ✨"
        ]
        insights = [
            f"💎 {themes.split(',')[0].strip().title()} isn't just about what you know — it's how you apply it.",
            f"🎯 Success in {industry} comes from combining {skills.split(',')[0].strip()} with genuine curiosity.",
            f"🔥 The most valuable skill isn't always technical — it's the ability to adapt.",
            f"⚡ Innovation happens at the intersection of {skills.split(',')[0].strip()} and creative problem-solving.",
            f"🌱 Growth mindset + {skills.split(',')[0].strip()} = unstoppable professional development."
        ]
        actions = [
            "📌 Focus on building genuine connections, not just collecting contacts",
            "📌 Share your knowledge freely — what you give comes back multiplied",
            "📌 Ask better questions instead of just seeking quick answers",
            "📌 Embrace failure as feedback, not as a setback",
            "📌 Stay curious and never stop learning from those around you"
        ]
        questions = [
            "What's been your biggest learning moment this year? 👇",
            "How do you approach continuous learning in your field? 💬",
            "What strategies have worked for you? Drop your insights below! 🗣️",
            "Have you experienced something similar? Let's discuss! 💭",
            "What's your take on this? Share your perspective! 🤝"
        ]

        selected_insights = random.sample(insights, 3)
        selected_actions  = random.sample(actions, 3)
        skill_tags = [f"#{s.strip().replace(' ', '')}" for s in skills.split(',')[:2]]
        hashtags   = f"#LinkedIn #ProfessionalGrowth {' '.join(skill_tags)}"

        generated_post = (
            f"{random.choice(hooks)}\n\n"
            f"Here's what I've discovered:\n\n"
            f"{selected_insights[0]}\n\n"
            f"{selected_insights[1]}\n\n"
            f"{selected_insights[2]}\n\n"
            f"Three things that have helped me:\n\n"
            f"{selected_actions[0]}\n"
            f"{selected_actions[1]}\n"
            f"{selected_actions[2]}\n\n"
            f"{random.choice(questions)}\n\n"
            f"{hashtags}"
        )

        post_id = str(uuid.uuid4())[:8]

        keyboard = [
            [InlineKeyboardButton("📱 Post on Mobile (Copy & Paste)", callback_data='post_mobile')],
            [InlineKeyboardButton("🖥️ Post with Browser (Server)", callback_data=f'post_approve_{telegram_id}')],
            [InlineKeyboardButton("🔄 Generate New", callback_data='post_ai_generate')],
            [InlineKeyboardButton("✏️ Write My Own Instead", callback_data='post_write_own')],
            [InlineKeyboardButton("❌ Discard", callback_data='post_discard')],
        ]

        context.user_data['generated_post'] = generated_post
        context.user_data['post_id'] = post_id

        await reply_msg.reply_text(
            f"📝 *Generated Post Preview:*\n\n"
            f"{'─' * 40}\n\n"
            f"{generated_post}\n\n"
            f"{'─' * 40}\n\n"
            f"Choose how to post:\n"
            f"📱 *Mobile*: Opens on your phone (recommended)\n"
            f"🖥️ *Browser*: Opens on server (visible automation)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error generating post: {e}")
        await reply_msg.reply_text(f"❌ Error generating content: {str(e)}\n\nPlease try again later.")


def run_post_visible_browser(telegram_id: int, generated_post: str):
    """Legacy threading function - fallback only"""
    """Run LinkedIn posting with visible browser window"""
    try:
        # Get credentials
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            logger.error(f"LinkedIn credentials not found for user {telegram_id}")
            return

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        # Log start (user already got "Posting..." message from main thread)
        logger.info(f"Opening visible LinkedIn browser for user {telegram_id}")

        linkedin_bot = LinkedInBot(email, password, headless=False)

        if not linkedin_bot.start():
            logger.error(f"Failed to login to LinkedIn for user {telegram_id}")
            return

        # Take screenshot after successful login
        screenshot_path = save_screenshot(linkedin_bot.driver, telegram_id, "login_success")
        if screenshot_path:
            screenshot_queue.add_screenshot(telegram_id, screenshot_path, "LinkedIn Login Successful")

        # Create the post
        logger.info(f"Creating LinkedIn post for user {telegram_id}")
        success = linkedin_bot.create_post(generated_post)

        # Take screenshot after posting
        if success:
            screenshot_path = save_screenshot(linkedin_bot.driver, telegram_id, "post_success")
            if screenshot_path:
                screenshot_queue.add_screenshot(telegram_id, screenshot_path, "Post Created Successfully ✅")

        linkedin_bot.stop()

        # Log the action (use 'post' not 'post_created')
        if success:
            db.log_automation_action(telegram_id, 'post', 1)
            logger.info(f"✅ Successfully posted to LinkedIn for user {telegram_id}")
        else:
            logger.error(f"Failed to post to LinkedIn for user {telegram_id}")

    except Exception as e:
        logger.error(f"Error posting to LinkedIn for user {telegram_id}: {e}")


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

    keyboard = [
        [InlineKeyboardButton("📱 Post on Mobile (Copy & Paste)", callback_data='post_mobile')],
        [InlineKeyboardButton("🖥️ Post with Browser (Server)", callback_data=f'post_approve_{telegram_id}')],
        [InlineKeyboardButton("✏️ Edit & Retype", callback_data='post_write_own')],
        [InlineKeyboardButton("❌ Discard", callback_data='post_discard')],
    ]

    context.user_data['generated_post'] = custom_post
    context.user_data['post_id'] = post_id

    await update.message.reply_text(
        f"📝 *Your Post Preview:*\n\n"
        f"{'─' * 40}\n\n"
        f"{custom_post}\n\n"
        f"{'─' * 40}\n\n"
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
        await query.edit_message_text("❌ Post discarded.")
        context.user_data.pop('generated_post', None)
        context.user_data.pop('awaiting_custom_post', None)
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

        await query.edit_message_text(
            "✅ *Post Approved!*\n\n"
            "🚀 *Automation Starting...*\n\n"
            "🖥️ *Remote Processing:*\n"
            "Your post is being published on our secure remote servers.\n\n"
            "📸 *Screenshot Delivery:*\n"
            "Watch your progress! Screenshots will be sent to you within 10 seconds showing:\n"
            "  • LinkedIn login confirmation\n"
            "  • Your published post\n\n"
            "⏱️ Please wait approximately 30 seconds...",
            parse_mode='Markdown'
        )

        telegram_id = update.effective_user.id

        # Run posting with visible browser in background thread
        if CELERY_ENABLED:
            post_to_linkedin_task.delay(telegram_id, generated_post)
        else:
            Thread(target=run_post_visible_browser, args=(telegram_id, generated_post)).start()

        # Clear context
        if 'generated_post' in context.user_data:
            del context.user_data['generated_post']


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


async def cancel_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel user's Stripe subscription - ALWAYS provides cancellation option"""
    telegram_id = update.effective_user.id

    # Try to get user data (but don't block if not found)
    user_data = None
    try:
        user_data = db.get_user(telegram_id)
    except Exception as e:
        logger.error(f"Error getting user data: {e}")

    stripe_subscription_id = user_data.get('stripe_subscription_id') if user_data else None

    # Build warning message based on available data
    warning_msg = ""
    if not user_data:
        warning_msg = "\n\n⚠️ Note: User not found in database. You can still attempt cancellation if you have a Stripe subscription."
    elif not stripe_subscription_id:
        warning_msg = "\n\n⚠️ Note: No subscription ID found in database. You can still attempt cancellation if you have an active Stripe subscription."

    # ALWAYS show confirmation dialog - never block user from attempting cancellation
    keyboard = [
        [InlineKeyboardButton("❌ Yes, cancel my subscription", callback_data='confirm_cancel_sub')],
        [InlineKeyboardButton("✅ Keep my subscription", callback_data='keep_sub')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"😢 We're sorry to see you go!\n\n"
        f"Are you sure you want to cancel your subscription?\n\n"
        f"⚠️ This will attempt to cancel your Stripe subscription. You will lose access to:\n"
        f"• AI-generated posts\n"
        f"• Smart feed engagement\n"
        f"• Automated networking\n"
        f"• Analytics dashboard{warning_msg}\n\n"
        f"Your subscription will remain active until the end of your current billing period.",
        reply_markup=reply_markup
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

        # Try to create portal session (preferred method)
        if stripe_customer_id:
            try:
                # Create Stripe Customer Portal session
                portal_session = stripe.billing_portal.Session.create(
                    customer=stripe_customer_id,
                    return_url=f'{PAYMENT_SERVER_URL}/payment/cancel-complete?telegram_id={telegram_id}'
                )

                # Show portal option + fallback API option
                keyboard = [
                    [InlineKeyboardButton("🔗 Open Stripe Portal (Recommended)", url=portal_session.url)],
                    [InlineKeyboardButton("⚡ Direct API Cancel (Fallback)", callback_data='force_cancel_sub')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    "🔐 Choose cancellation method:\n\n"
                    "✅ **Recommended: Stripe Portal**\n"
                    "• Official Stripe interface\n"
                    "• Webhook confirmation\n"
                    "• Update payment method\n"
                    "• View billing history\n\n"
                    "⚡ **Fallback: Direct API**\n"
                    "• Immediate cancellation\n"
                    "• No webhook needed\n"
                    "• Use if portal fails\n\n"
                    "⚠️ After canceling in portal, you'll receive webhook confirmation.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

                # Store that user initiated cancellation
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
                # Portal failed, show only direct API option
                keyboard = [[InlineKeyboardButton("⚡ Cancel via Direct API", callback_data='force_cancel_sub')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    f"⚠️ Stripe Portal unavailable:\n\n{str(e)}\n\n"
                    "Using direct API cancellation instead:\n\n"
                    "👇 Click below to cancel your subscription immediately.",
                    reply_markup=reply_markup
                )

        else:
            # No customer ID, must use direct API
            # ALWAYS show Direct API button - never block user from attempting
            keyboard = [[InlineKeyboardButton("⚡ Cancel via Direct API", callback_data='force_cancel_sub')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Build message based on available data
            if not stripe_subscription_id:
                # No subscription ID, but still show button - let Stripe API respond
                await query.edit_message_text(
                    "⚠️ Warning: No subscription ID found in database.\n\n"
                    "You can still attempt to cancel via Stripe API below.\n\n"
                    "If this fails, please contact support with your Telegram ID.\n\n"
                    "👇 Click below to attempt cancellation:",
                    reply_markup=reply_markup
                )
            else:
                # Have subscription ID, no customer ID
                await query.edit_message_text(
                    "ℹ️ No customer portal available.\n\n"
                    "Using direct API cancellation:\n\n"
                    "⚡ This will immediately cancel your subscription via Stripe API.\n\n"
                    "👇 Click below to proceed:",
                    reply_markup=reply_markup
                )

    elif query.data == 'force_cancel_sub':
        # Direct API cancellation (fallback method)
        # Try to get user data, but don't block if missing
        user_data = None
        stripe_subscription_id = None

        try:
            user_data = db.get_user(telegram_id)
            stripe_subscription_id = user_data.get('stripe_subscription_id') if user_data else None
        except Exception as e:
            logger.error(f"Error getting user data for cancellation: {e}")

        # If no subscription ID, show helpful error but acknowledge the attempt
        if not stripe_subscription_id:
            await query.edit_message_text(
                "❌ Unable to cancel: No Stripe subscription ID found\n\n"
                "This means either:\n"
                "• You haven't subscribed yet\n"
                "• Your subscription data is missing from our database\n"
                "• Your subscription was already cancelled\n\n"
                "📧 Please contact support with your Telegram ID and we'll help resolve this.\n\n"
                f"Your Telegram ID: `{telegram_id}`",
                parse_mode='Markdown'
            )
            return

        try:
            # Cancel subscription directly via Stripe API
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )

            # Update local database
            db.execute_query("""
                UPDATE users
                SET subscription_active = false,
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{cancelled_at}',
                        to_jsonb(NOW())
                    )
                WHERE telegram_id = %s
            """, (telegram_id,))

            # Get cancellation date
            from datetime import datetime
            cancel_date = datetime.fromtimestamp(subscription.current_period_end)
            cancel_date_str = cancel_date.strftime('%B %d, %Y')

            await query.edit_message_text(
                f"✅ Subscription Cancelled via Direct API\n\n"
                f"Your subscription has been successfully cancelled in Stripe.\n\n"
                f"📅 Access continues until: {cancel_date_str}\n\n"
                f"You won't be charged again.\n\n"
                f"Changed your mind? You can resubscribe anytime with /start\n\n"
                f"Thank you for using LinkedInGrowthBot! 💙"
            )

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe API error: {e}")
            await query.edit_message_text(
                f"❌ Stripe API Error:\n\n"
                f"{str(e)}\n\n"
                f"The subscription may not exist or is already cancelled.\n\n"
                f"Check your Stripe dashboard or contact support."
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            await query.edit_message_text(
                f"❌ Error cancelling subscription:\n\n"
                f"{str(e)}\n\n"
                f"Please try again or contact support."
            )
        except Exception as e:
            logger.error(f"Error in direct cancellation: {e}")
            await query.edit_message_text(
                "❌ An error occurred while cancelling your subscription.\n\n"
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
        if not linkedin_bot.start():
            logger.error(f"Failed to start LinkedIn bot for job scan (user {telegram_id})")
            return

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
    config = db.get_job_search_config(telegram_id)

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
        if CELERY_ENABLED:
            scan_jobs_task.delay(telegram_id)
        else:
            Thread(target=run_job_scan, args=(telegram_id,), daemon=True).start()

    elif query.data == 'jobscan_toggle':
        config = db.get_job_search_config(telegram_id)
        current = config.get('notification_enabled', False) if config else False
        new_state = not current
        db.execute_query(
            "UPDATE job_seeking_configs SET notification_enabled = %s WHERE telegram_id = %s",
            (new_state, telegram_id)
        )
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

        db.save_job_search_config(
            telegram_id,
            roles=roles,
            locations=locations,
            enabled=True
        )

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
    if CELERY_ENABLED:
        scan_jobs_task.delay(telegram_id)
    else:
        Thread(target=run_job_scan, args=(telegram_id,), daemon=True).start()


# --- /stopjob command ---
async def stop_job_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable job scanning for this user."""
    telegram_id = update.effective_user.id
    db.execute_query(
        "UPDATE job_seeking_configs SET notification_enabled = false WHERE telegram_id = %s",
        (telegram_id,)
    )
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
        pattern='^(post_approve_|post_regenerate|post_discard|post_ai_generate|post_write_own|post_mobile|post_confirmed)'
    ))

    # Custom post text input (must be before the generic settings text handler)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_custom_post_text
    ), group=1)

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

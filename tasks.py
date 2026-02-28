#!/usr/bin/env python3
"""
Celery Task Definitions
Background tasks for LinkedIn automation
Replaces threading approach with distributed task queue
"""

import os
import time
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from celery_app import app
from browser_pool import get_browser_pool
from linkedin_bot import LinkedInBot
from bot_database_postgres import BotDatabase
from screenshot_handler import save_screenshot, screenshot_queue
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Initialize database and encryption
db = BotDatabase()
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if ENCRYPTION_KEY:
    cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
else:
    logger.warning("ENCRYPTION_KEY not set, generating temporary key")
    cipher = Fernet(Fernet.generate_key())

MAX_LOGIN_ATTEMPTS = 3


def decrypt_password(encrypted: bytes) -> str:
    """Decrypt LinkedIn password"""
    try:
        return cipher.decrypt(encrypted).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt password: {e}")
        raise


def login_with_retry(linkedin_bot, telegram_id, max_attempts=MAX_LOGIN_ATTEMPTS):
    """
    Attempt LinkedIn login up to max_attempts times with progress notifications.

    Returns True on success, False on failure (sends failure message to user).
    """
    for attempt in range(1, max_attempts + 1):
        send_telegram_notification.delay(
            telegram_id,
            f"Signing in to LinkedIn... (attempt {attempt}/{max_attempts})"
        )
        if linkedin_bot.start():
            return True
        if attempt < max_attempts:
            send_telegram_notification.delay(
                telegram_id,
                f"Sign-in attempt {attempt} failed. Retrying in 10 seconds..."
            )
            time.sleep(10)

    send_telegram_notification.delay(
        telegram_id,
        f"LinkedIn sign-in failed after {max_attempts} attempts.\n\n"
        "Possible reasons:\n"
        "- Incorrect email or password\n"
        "- LinkedIn is blocking our server device\n\n"
        "What to do:\n"
        "1. Check your credentials: /settings > Update LinkedIn Credentials\n"
        "2. Open LinkedIn in your browser, sign in manually, and approve any "
        "security prompts (e.g., 'Was this you?')\n"
        "3. Try again after approving"
    )
    return False


def take_task_screenshot(driver, telegram_id, action, description):
    """Save a screenshot and queue it for sending to user."""
    path = save_screenshot(driver, telegram_id, action)
    if path:
        screenshot_queue.add_screenshot(telegram_id, path, description)


def get_linkedin_bot(telegram_id: int, browser_context=None):
    """
    Initialize LinkedIn bot for a user, always with modules ready.

    Args:
        telegram_id: User's Telegram ID
        browser_context: Optional browser context from pool

    Returns:
        LinkedInBot instance with driver set up and modules initialized

    Raises:
        ValueError: If credentials not found
    """
    creds = db.get_linkedin_credentials(telegram_id)
    if not creds:
        raise ValueError(f"No LinkedIn credentials found for user {telegram_id}")

    email = creds['email']
    password = decrypt_password(creds['encrypted_password'])

    linkedin_bot = LinkedInBot(
        email=email,
        password=password,
        headless=True,
        driver=browser_context.driver if browser_context else None
    )

    # Always ensure driver is set up and modules are initialized.
    # Without this, posting_module / engagement_module etc. stay None
    # when a cached (already-logged-in) browser session is reused.
    linkedin_bot.setup_driver()
    linkedin_bot.initialize_modules()

    return linkedin_bot


@app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def post_to_linkedin_task(self, telegram_id: int, content: str, media: str = None):
    """
    Background task for LinkedIn posting

    Args:
        telegram_id: User's Telegram ID
        content: Post content text
        media: Optional media file path

    Returns:
        dict with success status and details
    """
    browser_context = None

    try:
        # Get browser from pool
        browser_pool = get_browser_pool()
        browser_context = browser_pool.acquire(telegram_id, timeout=120)

        # Initialize bot
        linkedin_bot = get_linkedin_bot(telegram_id, browser_context)

        # Login if needed
        if not browser_context.is_logged_in:
            logger.info(f"Logging in to LinkedIn for user {telegram_id}")
            if not login_with_retry(linkedin_bot, telegram_id):
                return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}
            browser_context.mark_logged_in()

        take_task_screenshot(linkedin_bot.driver, telegram_id, "login_success", "LinkedIn Sign-In Successful")
        send_telegram_notification.delay(telegram_id, "Signed in successfully. Creating your post...")

        # Create post
        logger.info(f"Creating post for user {telegram_id}")
        success = linkedin_bot.create_post(content, media)

        if not success:
            take_task_screenshot(linkedin_bot.driver, telegram_id, "post_failed", "Post Creation Failed")
            raise Exception("Failed to create LinkedIn post")

        take_task_screenshot(linkedin_bot.driver, telegram_id, "post_success", "Post Created Successfully")

        # Log action to database
        db.log_automation_action(telegram_id, 'post', 1, session_id=self.request.id)

        # Send success notification
        send_telegram_notification.delay(
            telegram_id,
            f"✅ Post Created Successfully!\n\n{content[:100]}..."
        )

        logger.info(f"Post task completed for user {telegram_id}")
        return {
            'success': True,
            'telegram_id': telegram_id,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Post task failed for user {telegram_id}: {e}")

        # Send failure notification
        send_telegram_notification.delay(
            telegram_id,
            f"❌ Post Failed: {str(e)}\n\nWe'll retry automatically."
        )

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            return {'success': False, 'error': str(e)}

    finally:
        # Clean up uploaded media file
        if media:
            try:
                import os
                if os.path.exists(media):
                    os.remove(media)
            except Exception:
                pass
        # Return browser to pool
        if browser_context:
            browser_pool.release(browser_context)


@app.task(bind=True, max_retries=2)
def engage_with_feed_task(self, telegram_id: int, max_engagements: int = 10):
    """
    Background task for feed engagement

    Args:
        telegram_id: User's Telegram ID
        max_engagements: Maximum posts to engage with

    Returns:
        dict with engagement statistics
    """
    browser_context = None

    try:
        # Get browser from pool
        browser_pool = get_browser_pool()
        browser_context = browser_pool.acquire(telegram_id, timeout=120)

        # Initialize bot
        linkedin_bot = get_linkedin_bot(telegram_id, browser_context)

        # Login if needed
        if not browser_context.is_logged_in:
            if not login_with_retry(linkedin_bot, telegram_id):
                return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}
            browser_context.mark_logged_in()

        take_task_screenshot(linkedin_bot.driver, telegram_id, "login_success", "LinkedIn Sign-In Successful")
        send_telegram_notification.delay(telegram_id, "Signed in successfully. Scrolling through your feed...")

        # Load engagement config
        linkedin_bot.load_engagement_config('data/engagement_config.json')

        # Perform engagement
        logger.info(f"Starting feed engagement for user {telegram_id}")
        posts_engaged = linkedin_bot.engage_with_feed(max_engagements=max_engagements)

        take_task_screenshot(linkedin_bot.driver, telegram_id, "engagement_complete", "Feed Engagement Complete")

        # Log stats
        db.log_automation_action(telegram_id, 'like', posts_engaged, session_id=self.request.id)

        # Send success notification
        send_telegram_notification.delay(
            telegram_id,
            f"✅ Engagement Complete!\n\n"
            f"Interacted with {posts_engaged} posts."
        )

        logger.info(f"Engagement task completed for user {telegram_id}: {posts_engaged} posts")
        return {
            'success': True,
            'posts_engaged': posts_engaged,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Engagement task failed for user {telegram_id}: {e}")
        send_telegram_notification.delay(
            telegram_id,
            f"❌ Engagement Failed: {str(e)}"
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)
        else:
            return {'success': False, 'error': str(e)}

    finally:
        if browser_context:
            browser_pool.release(browser_context)


@app.task(bind=True, max_retries=2)
def reply_engagement_task(self, telegram_id: int, max_replies: int = 5):
    """
    Background task for replying to comments

    Args:
        telegram_id: User's Telegram ID
        max_replies: Maximum comments to reply to

    Returns:
        dict with reply statistics
    """
    browser_context = None

    try:
        browser_pool = get_browser_pool()
        browser_context = browser_pool.acquire(telegram_id, timeout=120)

        linkedin_bot = get_linkedin_bot(telegram_id, browser_context)

        if not browser_context.is_logged_in:
            if not login_with_retry(linkedin_bot, telegram_id):
                return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}
            browser_context.mark_logged_in()

        take_task_screenshot(linkedin_bot.driver, telegram_id, "login_success", "LinkedIn Sign-In Successful")
        send_telegram_notification.delay(telegram_id, "Signed in successfully. Loading notifications and comments...")

        # Load reply templates
        linkedin_bot.load_reply_templates('data/reply_templates.json')

        # Reply to comments
        logger.info(f"Starting reply engagement for user {telegram_id}")
        send_telegram_notification.delay(telegram_id, "Scanning your posts for comments to reply to...")
        replies_sent = linkedin_bot.reply_to_comments(max_replies=max_replies)

        take_task_screenshot(linkedin_bot.driver, telegram_id, "reply_complete", "Reply Engagement Complete")

        # Log stats
        db.log_automation_action(telegram_id, 'comment', replies_sent, session_id=self.request.id)

        send_telegram_notification.delay(
            telegram_id,
            f"✅ Reply Engagement Complete!\n\n"
            f"Replied to {replies_sent} comments."
        )

        logger.info(f"Reply task completed for user {telegram_id}: {replies_sent} replies")
        return {
            'success': True,
            'replies_sent': replies_sent,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Reply task failed for user {telegram_id}: {e}")
        send_telegram_notification.delay(telegram_id, f"❌ Reply Engagement Failed: {str(e)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)
        else:
            return {'success': False, 'error': str(e)}

    finally:
        if browser_context:
            browser_pool.release(browser_context)


@app.task(bind=True, max_retries=2)
def send_connection_requests_task(self, telegram_id: int, count: int = 10):
    """
    Background task for sending connection requests

    Args:
        telegram_id: User's Telegram ID
        count: Number of connection requests to send

    Returns:
        dict with connection statistics
    """
    browser_context = None

    try:
        browser_pool = get_browser_pool()
        browser_context = browser_pool.acquire(telegram_id, timeout=120)

        linkedin_bot = get_linkedin_bot(telegram_id, browser_context)

        if not browser_context.is_logged_in:
            if not login_with_retry(linkedin_bot, telegram_id):
                return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}
            browser_context.mark_logged_in()

        take_task_screenshot(linkedin_bot.driver, telegram_id, "login_success", "LinkedIn Sign-In Successful")
        send_telegram_notification.delay(telegram_id, "Signed in successfully. Searching for relevant professionals...")

        # TODO: Implement connection request logic
        # This depends on your existing implementation
        logger.info(f"Sending connection requests for user {telegram_id}")

        send_telegram_notification.delay(telegram_id, "Sending personalized connection requests...")
        # Placeholder - replace with actual logic
        connections_sent = 0  # linkedin_bot.send_connection_requests(count)

        take_task_screenshot(linkedin_bot.driver, telegram_id, "connection_complete", "Connection Requests Complete")

        # Log stats
        db.log_automation_action(telegram_id, 'connection', connections_sent, session_id=self.request.id)

        send_telegram_notification.delay(
            telegram_id,
            f"✅ Connection Requests Sent!\n\n"
            f"Sent {connections_sent} connection requests."
        )

        return {
            'success': True,
            'connections_sent': connections_sent,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Connection task failed for user {telegram_id}: {e}")
        send_telegram_notification.delay(telegram_id, f"❌ Connection Requests Failed: {str(e)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)
        else:
            return {'success': False, 'error': str(e)}

    finally:
        if browser_context:
            browser_pool.release(browser_context)


@app.task(bind=True, max_retries=2)
def autopilot_task(self, telegram_id: int, max_posts_to_engage: int = 10, max_connections: int = 5):
    """
    Background task for full autopilot mode

    Args:
        telegram_id: User's Telegram ID
        max_posts_to_engage: Maximum posts to engage with
        max_connections: Maximum connection requests to send

    Returns:
        dict with autopilot statistics
    """
    browser_context = None

    try:
        browser_pool = get_browser_pool()
        browser_context = browser_pool.acquire(telegram_id, timeout=120)

        linkedin_bot = get_linkedin_bot(telegram_id, browser_context)

        if not browser_context.is_logged_in:
            if not login_with_retry(linkedin_bot, telegram_id):
                return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}
            browser_context.mark_logged_in()

        take_task_screenshot(linkedin_bot.driver, telegram_id, "login_success", "LinkedIn Sign-In Successful")
        send_telegram_notification.delay(telegram_id, "Signed in successfully. Starting autopilot tasks...")

        # Load configs
        linkedin_bot.load_engagement_config('data/engagement_config.json')
        linkedin_bot.load_reply_templates('data/reply_templates.json')

        # Run full autopilot
        logger.info(f"Starting autopilot for user {telegram_id}")
        send_telegram_notification.delay(telegram_id, "Generating and posting AI content...")
        results = linkedin_bot.run_full_autopilot(
            max_posts_to_engage=max_posts_to_engage,
            max_connections=max_connections
        )

        take_task_screenshot(linkedin_bot.driver, telegram_id, "autopilot_complete", "Autopilot Complete")

        # Log all actions
        if results.get('post_created'):
            db.log_automation_action(telegram_id, 'post', 1, session_id=self.request.id)
        if results.get('posts_engaged'):
            db.log_automation_action(telegram_id, 'like', results['posts_engaged'], session_id=self.request.id)
        if results.get('connections_sent'):
            db.log_automation_action(telegram_id, 'connection', results['connections_sent'], session_id=self.request.id)

        send_telegram_notification.delay(
            telegram_id,
            f"✅ Autopilot Complete!\n\n"
            f"📝 Posts: {1 if results.get('post_created') else 0}\n"
            f"👍 Engagements: {results.get('posts_engaged', 0)}\n"
            f"🤝 Connections: {results.get('connections_sent', 0)}"
        )

        logger.info(f"Autopilot task completed for user {telegram_id}")
        return {
            'success': True,
            'results': results,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Autopilot task failed for user {telegram_id}: {e}")
        send_telegram_notification.delay(telegram_id, f"❌ Autopilot Failed: {str(e)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=180)
        else:
            return {'success': False, 'error': str(e)}

    finally:
        if browser_context:
            browser_pool.release(browser_context)


@app.task(bind=True, max_retries=1)
def scan_jobs_task(self, telegram_id: int):
    """
    Background task for job scanning

    Args:
        telegram_id: User's Telegram ID

    Returns:
        dict with job scan statistics
    """
    # Job scanning can run headless without browser pool
    # Since it's less resource-intensive
    try:
        creds = db.get_linkedin_credentials(telegram_id)
        if not creds:
            raise ValueError(f"No credentials for user {telegram_id}")

        email = creds['email']
        password = decrypt_password(creds['encrypted_password'])

        linkedin_bot = LinkedInBot(email, password, headless=True)

        if not login_with_retry(linkedin_bot, telegram_id):
            return {'success': False, 'error': 'LinkedIn login failed after 3 attempts'}

        send_telegram_notification.delay(telegram_id, "Signed in. Scanning for new job postings...")

        # TODO: Implement job scanning logic
        logger.info(f"Scanning jobs for user {telegram_id}")
        jobs_found = 0  # linkedin_bot.scan_jobs()

        send_telegram_notification.delay(
            telegram_id,
            f"✅ Job Scan Complete!\n\n"
            f"Found {jobs_found} new job postings."
        )

        return {
            'success': True,
            'jobs_found': jobs_found,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Job scan task failed for user {telegram_id}: {e}")
        send_telegram_notification.delay(telegram_id, f"❌ Job Scan Failed: {str(e)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)
        else:
            return {'success': False, 'error': str(e)}


@app.task
def send_telegram_notification(telegram_id: int, message: str):
    """
    Send Telegram notification (lightweight task)

    Args:
        telegram_id: User's Telegram ID
        message: Message to send

    Note:
        This task runs in a separate lightweight worker
        Requires telegram bot application to be running
    """
    try:
        # Import here to avoid circular imports
        from telegram import Bot
        import asyncio

        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set, cannot send notification")
            return

        async def send():
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=telegram_id, text=message)

        # Run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(send())
        logger.info(f"Sent notification to user {telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send Telegram notification to {telegram_id}: {e}")

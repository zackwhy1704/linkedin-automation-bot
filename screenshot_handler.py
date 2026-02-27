"""
Screenshot Handler for Telegram Bot
Manages screenshot capture and sending to users
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Screenshot directory
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

class ScreenshotQueue:
    """Manages screenshots to be sent to users"""

    def __init__(self):
        self.queue = {}  # {telegram_id: [screenshot_paths]}

    def add_screenshot(self, telegram_id: int, screenshot_path: str, description: str = ""):
        """Add a screenshot to the queue for a user"""
        if telegram_id not in self.queue:
            self.queue[telegram_id] = []

        self.queue[telegram_id].append({
            'path': screenshot_path,
            'description': description,
            'timestamp': datetime.now()
        })
        logger.info(f"Screenshot queued for user {telegram_id}: {screenshot_path}")

    def get_screenshots(self, telegram_id: int):
        """Get all screenshots for a user and clear the queue"""
        screenshots = self.queue.get(telegram_id, [])
        if telegram_id in self.queue:
            del self.queue[telegram_id]
        return screenshots

    def has_screenshots(self, telegram_id: int):
        """Check if user has pending screenshots"""
        return telegram_id in self.queue and len(self.queue[telegram_id]) > 0


# Global screenshot queue
screenshot_queue = ScreenshotQueue()


def save_screenshot(driver, telegram_id: int, action: str) -> str:
    """
    Save a screenshot from Selenium WebDriver

    Args:
        driver: Selenium WebDriver instance
        telegram_id: User's Telegram ID
        action: Description of what was done (e.g., 'post', 'login', 'engage')

    Returns:
        str: Path to saved screenshot
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{telegram_id}_{action}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename

        # Take screenshot
        driver.save_screenshot(str(filepath))

        logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Error saving screenshot: {e}")
        return None


async def send_queued_screenshots(bot, telegram_id: int):
    """
    Send all queued screenshots to a user

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
    """
    screenshots = screenshot_queue.get_screenshots(telegram_id)

    if not screenshots:
        return

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=f"📸 Here are {len(screenshots)} screenshot(s) from your automation:"
        )

        for screenshot in screenshots:
            filepath = screenshot['path']
            description = screenshot['description']

            if os.path.exists(filepath):
                with open(filepath, 'rb') as photo:
                    caption = f"✅ {description}" if description else "Screenshot"
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo,
                        caption=caption
                    )

                # Clean up screenshot file after sending
                try:
                    os.remove(filepath)
                    logger.info(f"Screenshot sent and deleted: {filepath}")
                except Exception as e:
                    logger.error(f"Error deleting screenshot {filepath}: {e}")
            else:
                logger.warning(f"Screenshot file not found: {filepath}")

    except Exception as e:
        logger.error(f"Error sending screenshots to user {telegram_id}: {e}")


# Helper function to check and send screenshots periodically
async def check_and_send_screenshots(bot):
    """
    Periodically check for new screenshots and send them
    This should be called in a background task
    """
    while True:
        try:
            # Check all users in queue
            telegram_ids = list(screenshot_queue.queue.keys())

            for telegram_id in telegram_ids:
                await send_queued_screenshots(bot, telegram_id)

            # Wait 5 seconds before checking again
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error in screenshot checker: {e}")
            await asyncio.sleep(5)

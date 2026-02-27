import schedule
import time
from linkedin_bot import LinkedInBot
from dotenv import load_dotenv
import os
import utils

# Load environment variables
load_dotenv()

# Configuration
EMAIL = os.getenv('LINKEDIN_EMAIL')
PASSWORD = os.getenv('LINKEDIN_PASSWORD')
HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'true'

# File paths
POSTS_FILE = 'data/posts_template.json'
REPLY_TEMPLATES_FILE = 'data/reply_templates.json'
ENGAGEMENT_CONFIG_FILE = 'data/engagement_config.json'

# Initialize bot (global for scheduled tasks)
bot = None

def initialize_bot():
    """Initialize the bot"""
    global bot
    utils.log("Initializing bot for scheduled tasks...")

    bot = LinkedInBot(EMAIL, PASSWORD, headless=HEADLESS)

    if bot.start():
        # Load configurations
        bot.load_reply_templates(REPLY_TEMPLATES_FILE)
        bot.load_engagement_config(ENGAGEMENT_CONFIG_FILE)
        return True
    else:
        utils.log("Failed to initialize bot", "ERROR")
        return False

def scheduled_posting():
    """Check and post scheduled posts (both manual and AI-generated)"""
    utils.log("=== Running Scheduled Posting Task ===")
    try:
        if bot:
            # Check manual scheduled posts
            bot.check_scheduled_posts(POSTS_FILE)
            # Check AI-generated scheduled posts (with video support)
            bot.check_ai_scheduled_posts()
        else:
            utils.log("Bot not initialized", "ERROR")
    except Exception as e:
        utils.log(f"Error in scheduled posting: {str(e)}", "ERROR")

def scheduled_engagement():
    """Engage with feed"""
    utils.log("=== Running Scheduled Engagement Task ===")
    try:
        if bot:
            # Engage with general feed
            bot.engage_with_feed(max_engagements=10)

            # Search and engage with specific hashtags
            hashtags = bot.engagement_module.engagement_config.get('hashtags_to_follow', [])
            for hashtag in hashtags[:3]:  # Limit to 3 hashtags per run
                bot.search_and_engage(hashtag, max_engagements=3)
                utils.random_delay(5, 10)
        else:
            utils.log("Bot not initialized", "ERROR")
    except Exception as e:
        utils.log(f"Error in scheduled engagement: {str(e)}", "ERROR")

def scheduled_reply():
    """Reply to comments"""
    utils.log("=== Running Scheduled Reply Task ===")
    try:
        if bot:
            bot.reply_to_comments(max_replies=5)
        else:
            utils.log("Bot not initialized", "ERROR")
    except Exception as e:
        utils.log(f"Error in scheduled reply: {str(e)}", "ERROR")

def scheduled_message_check():
    """Check and respond to messages"""
    utils.log("=== Running Scheduled Message Check ===")
    try:
        if bot:
            response_templates = [
                "Thanks for reaching out! I'll get back to you soon.",
                "I appreciate your message! Will respond shortly.",
                "Thanks for connecting! Talk soon."
            ]
            bot.check_messages(auto_respond=True, response_template=response_templates)
        else:
            utils.log("Bot not initialized", "ERROR")
    except Exception as e:
        utils.log(f"Error in scheduled message check: {str(e)}", "ERROR")

def setup_schedule():
    """Setup the schedule for all tasks"""
    utils.log("Setting up schedule...")

    # Check for scheduled posts every 30 minutes
    schedule.every(30).minutes.do(scheduled_posting)

    # Engage with feed twice a day
    schedule.every().day.at("09:00").do(scheduled_engagement)
    schedule.every().day.at("17:00").do(scheduled_engagement)

    # Reply to comments three times a day
    schedule.every().day.at("10:00").do(scheduled_reply)
    schedule.every().day.at("14:00").do(scheduled_reply)
    schedule.every().day.at("18:00").do(scheduled_reply)

    # Check messages every 2 hours
    schedule.every(2).hours.do(scheduled_message_check)

    utils.log("Schedule setup complete!", "SUCCESS")
    utils.log("Tasks scheduled:")
    utils.log("  - Scheduled posts: Every 30 minutes")
    utils.log("  - Feed engagement: 9:00 AM and 5:00 PM daily")
    utils.log("  - Reply to comments: 10:00 AM, 2:00 PM, 6:00 PM daily")
    utils.log("  - Message check: Every 2 hours")

def run_scheduler():
    """Run the scheduler"""
    utils.log("LinkedIn Automation Bot - Scheduler Started", "SUCCESS")

    # Initialize bot
    if not initialize_bot():
        utils.log("Failed to start bot. Exiting.", "ERROR")
        return

    # Setup schedule
    setup_schedule()

    # Run scheduled tasks
    utils.log("Bot is now running. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        utils.log("\nStopping scheduler...", "WARNING")
        if bot:
            bot.stop()
        utils.log("Scheduler stopped", "SUCCESS")

if __name__ == "__main__":
    run_scheduler()

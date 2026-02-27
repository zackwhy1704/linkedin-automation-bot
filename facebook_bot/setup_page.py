"""
Facebook Page Setup Helper
Configure Get Started button, Persistent Menu, and Greeting Text
"""
import os
import requests
import logging
from dotenv import load_dotenv
from facebook_bot.config import PAGE_ACCESS_TOKEN, AGENT_NAME
from facebook_bot.templates import MessageTemplates

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


def setup_get_started_button():
    """Configure Get Started button"""
    url = f"{GRAPH_API_URL}/me/messenger_profile"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "get_started": {
            "payload": "GET_STARTED"
        }
    }

    try:
        response = requests.post(url, params=params, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Get Started button configured")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set Get Started button: {e}")
        return False


def setup_greeting_text():
    """Configure greeting text shown before user starts conversation"""
    url = f"{GRAPH_API_URL}/me/messenger_profile"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "greeting": [
            {
                "locale": "default",
                "text": f"Hi! I'm {AGENT_NAME}'s assistant. I help with property buying, selling, and valuations in Singapore. Click Get Started to begin! 🏠"
            }
        ]
    }

    try:
        response = requests.post(url, params=params, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Greeting text configured")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set greeting text: {e}")
        return False


def setup_persistent_menu():
    """Configure persistent menu (hamburger menu in Messenger)"""
    templates = MessageTemplates()
    menu_config = templates.persistent_menu()

    url = f"{GRAPH_API_URL}/me/messenger_profile"
    params = {"access_token": PAGE_ACCESS_TOKEN}

    try:
        response = requests.post(url, params=params, json=menu_config, timeout=10)
        response.raise_for_status()
        logger.info("✅ Persistent menu configured")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set persistent menu: {e}")
        return False


def delete_messenger_profile(field: str):
    """Delete a messenger profile field (use to reset)"""
    url = f"{GRAPH_API_URL}/me/messenger_profile"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "fields": [field]
    }

    try:
        response = requests.delete(url, params=params, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Deleted {field}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete {field}: {e}")
        return False


def get_messenger_profile():
    """Get current messenger profile settings"""
    url = f"{GRAPH_API_URL}/me/messenger_profile"
    params = {
        "access_token": PAGE_ACCESS_TOKEN,
        "fields": "get_started,greeting,persistent_menu"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        logger.info("Current Messenger Profile:")
        logger.info("-" * 50)

        if 'data' in data and len(data['data']) > 0:
            for item in data['data']:
                if 'get_started' in item:
                    logger.info(f"Get Started: {item['get_started']}")
                if 'greeting' in item:
                    logger.info(f"Greeting: {item['greeting']}")
                if 'persistent_menu' in item:
                    logger.info(f"Persistent Menu: Configured")
        else:
            logger.info("No profile settings configured yet")

        logger.info("-" * 50)
        return data

    except Exception as e:
        logger.error(f"❌ Failed to get profile: {e}")
        return None


def setup_facebook_page():
    """Run complete page setup"""
    logger.info("=" * 60)
    logger.info("FACEBOOK PAGE SETUP")
    logger.info("=" * 60)

    if not PAGE_ACCESS_TOKEN:
        logger.error("FACEBOOK_PAGE_ACCESS_TOKEN not set in .env")
        return False

    logger.info(f"Page Access Token: {PAGE_ACCESS_TOKEN[:20]}...")

    # Get current settings
    logger.info("\n1. Checking current settings...")
    get_messenger_profile()

    # Setup components
    logger.info("\n2. Configuring Get Started button...")
    setup_get_started_button()

    logger.info("\n3. Configuring greeting text...")
    setup_greeting_text()

    logger.info("\n4. Configuring persistent menu...")
    setup_persistent_menu()

    # Verify
    logger.info("\n5. Verifying configuration...")
    get_messenger_profile()

    logger.info("\n" + "=" * 60)
    logger.info("✅ SETUP COMPLETE!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Visit your Facebook Page")
    logger.info("2. Click 'Message' button")
    logger.info("3. You should see the greeting text")
    logger.info("4. Click 'Get Started' to test the bot")
    logger.info("=" * 60)

    return True


def reset_facebook_page():
    """Reset all messenger profile settings"""
    logger.info("Resetting Facebook Page settings...")

    delete_messenger_profile("get_started")
    delete_messenger_profile("greeting")
    delete_messenger_profile("persistent_menu")

    logger.info("✅ All settings reset")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_facebook_page()
    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        get_messenger_profile()
    else:
        setup_facebook_page()

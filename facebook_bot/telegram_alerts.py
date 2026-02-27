"""
Telegram Agent Alerts
Sends real-time notifications to agent when hot leads arrive
"""
import os
import logging
import asyncio
import requests
from typing import Optional
from facebook_bot.db_handler import FacebookBotDB
from facebook_bot.config import AGENT_NAME, AGENT_PHONE

logger = logging.getLogger(__name__)


class TelegramAlerts:
    """Send Facebook bot alerts to agent's Telegram"""

    def __init__(self, bot_token: str, agent_chat_id: str):
        """
        Args:
            bot_token: Telegram bot token
            agent_chat_id: Agent's Telegram chat ID
        """
        self.bot_token = bot_token
        self.agent_chat_id = agent_chat_id
        self.db = FacebookBotDB()
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to agent's Telegram"""
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.agent_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

    async def process_pending_alerts(self):
        """Fetch and send all pending alerts"""
        try:
            alerts = self.db.get_pending_alerts()

            for alert in alerts:
                message = self.format_alert_message(alert)
                success = self.send_message(message)

                if success:
                    self.db.mark_alert_sent(alert['id'])
                    logger.info(f"Alert {alert['id']} sent to Telegram")

                # Small delay between messages
                await asyncio.sleep(0.5)

            if alerts:
                logger.info(f"Processed {len(alerts)} pending alerts")

        except Exception as e:
            logger.error(f"Error processing pending alerts: {e}", exc_info=True)

    def format_alert_message(self, alert: dict) -> str:
        """
        Format alert as rich Telegram message with HTML formatting

        Alert contains: id, lead_id, alert_type, alert_message, sent_at,
                        facebook_user_id, full_name, phone, lead_score
        """
        alert_type = alert.get('alert_type', 'notification')
        lead_score = alert.get('lead_score', 0)
        full_name = alert.get('full_name') or 'Unknown'
        phone = alert.get('phone') or 'Not provided'
        facebook_user_id = alert.get('facebook_user_id', '')

        # Score emoji
        if lead_score >= 8:
            score_emoji = "🔥🔥🔥"
        elif lead_score >= 7:
            score_emoji = "🔥🔥"
        else:
            score_emoji = "⭐"

        # Header based on alert type
        if alert_type == 'hot_lead':
            header = f"{score_emoji} <b>HOT LEAD ALERT!</b> {score_emoji}"
        elif alert_type == 'urgent_request':
            header = "⚡ <b>URGENT REQUEST</b> ⚡"
        elif alert_type == 'high_value':
            header = "💎 <b>HIGH VALUE LEAD</b> 💎"
        else:
            header = "📢 <b>NEW LEAD</b>"

        # Build message
        message_parts = [
            header,
            "",
            f"<b>Name:</b> {full_name}",
            f"<b>Phone:</b> {phone}",
            f"<b>Score:</b> {lead_score}/10",
            "",
            f"<b>Details:</b>",
            alert.get('alert_message', 'New lead inquiry'),
            "",
            f"<b>Facebook:</b> fb.com/{facebook_user_id}",
            f"<b>Messenger:</b> m.me/{facebook_user_id}",
            "",
            f"━━━━━━━━━━━━━━━━━━",
            f"From: {AGENT_NAME}'s Facebook Bot 🤖"
        ]

        return "\n".join(message_parts)

    async def send_daily_summary(self):
        """Send daily performance summary to agent"""
        try:
            stats = self.db.get_stats(days=1)

            summary = (
                f"📊 <b>Daily Facebook Bot Summary</b>\n\n"
                f"<b>Total Leads:</b> {stats['total_leads']}\n"
                f"<b>Hot Leads (7+):</b> {stats['hot_leads']} 🔥\n"
                f"<b>Avg Score:</b> {stats['avg_score']}/10\n\n"
                f"Keep up the great work! 💪"
            )

            self.send_message(summary)

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    async def start_alert_worker(self, interval: int = 30):
        """
        Background worker that checks for pending alerts every N seconds

        Args:
            interval: Check interval in seconds (default 30)
        """
        logger.info(f"Starting Telegram alert worker (interval: {interval}s)")

        while True:
            try:
                await self.process_pending_alerts()
            except Exception as e:
                logger.error(f"Alert worker error: {e}")

            await asyncio.sleep(interval)


async def run_alert_worker():
    """Standalone function to run alert worker"""
    from dotenv import load_dotenv
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    agent_chat_id = os.getenv("AGENT_TELEGRAM_ID")

    if not bot_token or not agent_chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or AGENT_TELEGRAM_ID not set in .env")
        return

    alerts = TelegramAlerts(bot_token, agent_chat_id)
    await alerts.start_alert_worker(interval=30)


if __name__ == "__main__":
    # Run standalone alert worker
    asyncio.run(run_alert_worker())

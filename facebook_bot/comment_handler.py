"""
Facebook Comment Auto-Reply Handler
Monitors post comments, replies publicly, sends DM follow-ups
"""
import logging
import requests
from facebook_bot.config import PAGE_ACCESS_TOKEN, COMMENT_TRIGGERS, AGENT_NAME

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


class CommentHandler:
    """Handles automatic comment replies and DM follow-ups"""

    def __init__(self, db, messenger_bot):
        self.db = db
        self.bot = messenger_bot

    async def handle_comment(self, post_id: str, comment_id: str,
                            commenter_id: str, comment_text: str):
        """
        Process new comment on page post.
        1. Check if already replied
        2. Check if comment contains trigger keywords
        3. Reply to comment publicly
        4. Send private DM to commenter
        """
        try:
            # Skip if already replied
            if self.db.has_replied_to_comment(comment_id):
                logger.info(f"Already replied to comment {comment_id}")
                return

            # Check if comment contains trigger keywords
            comment_lower = comment_text.lower()
            should_reply = any(
                trigger.lower() in comment_lower
                for trigger in COMMENT_TRIGGERS
            )

            if not should_reply:
                logger.info(f"Comment doesn't contain triggers: {comment_text}")
                return

            # Generate reply based on comment content
            reply_text = self.generate_reply(comment_text)

            # Post public reply
            reply_success = self.reply_to_comment(comment_id, reply_text)

            # Send DM to commenter
            dm_sent = False
            if reply_success:
                dm_sent = await self.send_dm_to_commenter(commenter_id, comment_text)

            # Save to database
            self.db.save_comment_reply(
                post_id=post_id,
                comment_id=comment_id,
                commenter_id=commenter_id,
                comment_text=comment_text,
                reply_text=reply_text,
                dm_sent=dm_sent
            )

            logger.info(f"Replied to comment {comment_id}, DM sent: {dm_sent}")

        except Exception as e:
            logger.error(f"Error handling comment: {e}", exc_info=True)

    def generate_reply(self, comment_text: str) -> str:
        """
        Generate appropriate public reply based on comment content.
        Keep it short and professional, then prompt to DM.
        """
        comment_lower = comment_text.lower()

        # Interested buyers
        if any(word in comment_lower for word in ['interested', 'interested!', 'pm', 'dm', 'price', 'how much']):
            return (
                f"Hi! Thanks for your interest! 😊 "
                f"I've sent you more details via DM. Check your messages!"
            )

        # Property type questions
        elif any(word in comment_lower for word in ['hdb', 'condo', 'landed', 'location', 'where']):
            return (
                f"Great question! I've sent you more details in your inbox. "
                f"Feel free to message me anytime! 💬"
            )

        # Valuation requests
        elif any(word in comment_lower for word in ['valuation', 'value', 'worth', 'sell']):
            return (
                f"I'd be happy to help with a free valuation! "
                f"Check your messages for more info. 📊"
            )

        # Viewing/appointment
        elif any(word in comment_lower for word in ['view', 'viewing', 'see', 'visit', 'appointment']):
            return (
                f"Let's arrange a viewing! "
                f"I've sent you a message to schedule. 📅"
            )

        # General interest
        else:
            return (
                f"Thanks for reaching out! "
                f"I've sent you more information via DM. Check your inbox! 💬"
            )

    def reply_to_comment(self, comment_id: str, reply_text: str) -> bool:
        """Post public reply to comment via Graph API"""
        url = f"{GRAPH_API_URL}/{comment_id}/comments"
        params = {"access_token": PAGE_ACCESS_TOKEN}
        data = {"message": reply_text}

        try:
            response = requests.post(url, params=params, data=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Public reply posted to comment {comment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reply to comment: {e}")
            return False

    async def send_dm_to_commenter(self, commenter_id: str, original_comment: str) -> bool:
        """
        Send private DM to user who commented.
        Start conversation flow based on their interest.
        """
        try:
            # Get or create lead
            lead = self.db.get_or_create_lead(
                facebook_user_id=commenter_id,
                source='comment'
            )

            # Get user profile
            profile = self.bot.get_user_profile(commenter_id)
            first_name = profile.get('first_name', 'there')

            # Update lead with profile info
            if profile:
                full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
                self.db.update_lead(
                    commenter_id,
                    username=first_name,
                    full_name=full_name or None
                )

            # Send personalized DM based on comment content
            dm_text = self.generate_dm_message(first_name, original_comment)
            self.bot.send_text(commenter_id, dm_text)

            # Show main menu
            await self.bot.show_main_menu(commenter_id, lead)

            # Save outgoing message
            self.db.save_message(
                lead_id=lead['id'],
                facebook_user_id=commenter_id,
                direction='outgoing',
                message_text=dm_text,
                message_type='comment_follow_up'
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send DM to commenter: {e}")
            return False

    def generate_dm_message(self, first_name: str, original_comment: str) -> str:
        """Generate personalized DM based on original comment"""
        comment_lower = original_comment.lower()

        # Price inquiry
        if any(word in comment_lower for word in ['price', 'how much', 'cost']):
            return (
                f"Hi {first_name}! 👋\n\n"
                f"Thanks for asking about pricing! I'd love to share more details.\n\n"
                f"To give you accurate information, I need to know a bit more about what you're looking for."
            )

        # Viewing request
        elif any(word in comment_lower for word in ['view', 'viewing', 'see', 'visit']):
            return (
                f"Hi {first_name}! 👋\n\n"
                f"I'd be happy to arrange a viewing for you!\n\n"
                f"Let me get some quick details so I can find the perfect time."
            )

        # Valuation
        elif any(word in comment_lower for word in ['valuation', 'value', 'worth', 'sell']):
            return (
                f"Hi {first_name}! 👋\n\n"
                f"I offer free property valuations! I can help you understand your property's current market value.\n\n"
                f"Let me get a few details from you."
            )

        # General interest
        else:
            return (
                f"Hi {first_name}! 👋\n\n"
                f"Thanks for your interest! I'm {AGENT_NAME}'s assistant.\n\n"
                f"I can help you with:\n"
                f"• Finding properties\n"
                f"• Property valuations\n"
                f"• Arranging viewings\n"
                f"• Answering your questions\n\n"
                f"What would you like to know?"
            )

    def like_comment(self, comment_id: str) -> bool:
        """Like a comment (optional engagement)"""
        url = f"{GRAPH_API_URL}/{comment_id}/likes"
        params = {"access_token": PAGE_ACCESS_TOKEN}

        try:
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            return True
        except Exception:
            return False

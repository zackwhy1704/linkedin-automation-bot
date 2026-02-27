"""
Facebook Messenger Bot Engine
Handles conversations, routes to flows, manages lead qualification
"""
import logging
import requests
from typing import Optional, Dict
from facebook_bot.config import PAGE_ACCESS_TOKEN, COMMENT_TRIGGERS, AGENT_NAME
from facebook_bot.db_handler import FacebookBotDB
from facebook_bot.templates import MessageTemplates
from facebook_bot.comment_handler import CommentHandler

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


class MessengerBot:
    """Main Messenger bot with conversation routing"""

    def __init__(self):
        self.db = FacebookBotDB()
        self.templates = MessageTemplates()
        self.comment_handler = CommentHandler(self.db, self)

    # ========== CORE MESSAGING ==========

    def send_message(self, recipient_id: str, message: dict) -> bool:
        """Send message via Facebook Graph API"""
        url = f"{GRAPH_API_URL}/me/messages"
        params = {"access_token": PAGE_ACCESS_TOKEN}
        payload = {
            "recipient": {"id": recipient_id},
            "message": message
        }

        try:
            response = requests.post(url, params=params, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Message sent to {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_text(self, recipient_id: str, text: str, quick_replies: list = None):
        """Send simple text message with optional quick replies"""
        message = {"text": text}
        if quick_replies:
            message["quick_replies"] = quick_replies
        self.send_message(recipient_id, message)

    def send_typing(self, recipient_id: str, on: bool = True):
        """Show/hide typing indicator"""
        url = f"{GRAPH_API_URL}/me/messages"
        params = {"access_token": PAGE_ACCESS_TOKEN}
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": "typing_on" if on else "typing_off"
        }
        try:
            requests.post(url, params=params, json=payload, timeout=5)
        except Exception:
            pass

    def get_user_profile(self, user_id: str) -> Dict:
        """Fetch user profile from Facebook"""
        url = f"{GRAPH_API_URL}/{user_id}"
        params = {
            "fields": "first_name,last_name,profile_pic",
            "access_token": PAGE_ACCESS_TOKEN
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {}

    # ========== MESSAGE HANDLERS ==========

    async def handle_message(self, sender_id: str, text: str):
        """Handle incoming text message"""
        try:
            # Get or create lead
            profile = self.get_user_profile(sender_id)
            full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
            lead = self.db.get_or_create_lead(
                facebook_user_id=sender_id,
                username=profile.get('first_name'),
                full_name=full_name or None
            )

            # Save incoming message
            self.db.save_message(
                lead_id=lead['id'],
                facebook_user_id=sender_id,
                direction='incoming',
                message_text=text
            )

            # Get conversation state
            state = lead.get('conversation_state') or 'main_menu'
            step = lead.get('conversation_step', 0)

            # Route to appropriate flow
            if state == 'main_menu' or text.lower() in ['menu', 'start', 'hi', 'hello']:
                await self.show_main_menu(sender_id, lead)

            elif state == 'property_search':
                await self.handle_property_search(sender_id, lead, text, step)

            elif state == 'valuation':
                await self.handle_valuation_flow(sender_id, lead, text, step)

            elif state == 'appointment':
                await self.handle_appointment_flow(sender_id, lead, text, step)

            elif state == 'contact_collection':
                await self.handle_contact_collection(sender_id, lead, text, step)

            else:
                # Fallback: show main menu
                await self.show_main_menu(sender_id, lead)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            self.send_text(sender_id, "Sorry, something went wrong. Type 'menu' to restart.")

    async def handle_postback(self, sender_id: str, payload: str):
        """Handle button clicks and quick reply selections"""
        try:
            lead = self.db.get_or_create_lead(sender_id)

            # Save postback as message
            self.db.save_message(
                lead_id=lead['id'],
                facebook_user_id=sender_id,
                direction='incoming',
                message_type='postback',
                payload=payload
            )

            # Route based on payload
            if payload == "GET_STARTED" or payload == "MAIN_MENU":
                await self.show_main_menu(sender_id, lead)

            elif payload.startswith("PROPERTY_"):
                await self.handle_property_search_postback(sender_id, lead, payload)

            elif payload.startswith("VALUATION_"):
                await self.handle_valuation_postback(sender_id, lead, payload)

            elif payload.startswith("APPOINTMENT_"):
                await self.handle_appointment_postback(sender_id, lead, payload)

            elif payload.startswith("INTENT_"):
                intent = payload.replace("INTENT_", "").lower()
                self.db.update_lead(sender_id, intent=intent)
                await self.show_main_menu(sender_id, lead)

            elif payload.startswith("TIMELINE_"):
                timeline = payload.replace("TIMELINE_", "")
                self.db.update_lead(sender_id, timeline=timeline)
                await self.ask_budget(sender_id, lead)

        except Exception as e:
            logger.error(f"Error handling postback: {e}", exc_info=True)

    async def handle_attachment(self, sender_id: str, attachments: list):
        """Handle image/file/location attachments"""
        lead = self.db.get_or_create_lead(sender_id)

        for attachment in attachments:
            att_type = attachment.get("type")

            if att_type == "location":
                # User shared location
                coords = attachment.get("payload", {}).get("coordinates", {})
                lat = coords.get("lat")
                lon = coords.get("long")
                self.send_text(
                    sender_id,
                    f"Thanks for sharing your location! Let me find properties near you."
                )

            elif att_type == "image":
                # User sent image (e.g., property photo for valuation)
                self.send_text(
                    sender_id,
                    "Thanks for the photo! I'll review it and get back to you."
                )

            else:
                self.send_text(sender_id, "Thanks for sending that!")

    async def handle_comment(self, post_id: str, comment_id: str,
                            commenter_id: str, comment_text: str):
        """Handle comments on page posts - delegate to comment handler"""
        await self.comment_handler.handle_comment(
            post_id, comment_id, commenter_id, comment_text
        )

    # ========== MAIN MENU ==========

    async def show_main_menu(self, sender_id: str, lead: Dict):
        """Show main menu with options"""
        self.db.update_lead(
            sender_id,
            conversation_state='main_menu',
            conversation_step=0
        )

        # First time user - welcome message
        if not lead.get('intent'):
            first_name = lead.get('username') or 'there'
            self.send_text(
                sender_id,
                f"Hi {first_name}! 👋\n\n"
                f"I'm {AGENT_NAME}'s assistant. I help with property buying, selling, and valuations in Singapore.\n\n"
                f"What are you interested in?"
            )

        # Send main menu quick replies
        message = self.templates.main_menu()
        self.send_message(sender_id, message)

        # Save outgoing message
        self.db.save_message(
            lead_id=lead['id'],
            facebook_user_id=sender_id,
            direction='outgoing',
            message_text="Main menu displayed"
        )

    # ========== PROPERTY SEARCH FLOW ==========

    async def handle_property_search(self, sender_id: str, lead: Dict, text: str, step: int):
        """Multi-step property search conversation"""
        if step == 0:
            # Ask property type
            self.send_message(sender_id, self.templates.property_type_selector())
            self.db.update_lead(sender_id, conversation_step=1)

        elif step == 1:
            # Save property type, ask location
            property_type = text.lower()
            self.db.update_lead(sender_id, property_type=property_type)
            self.send_text(
                sender_id,
                "Great! Which area are you looking at?\n\n"
                "E.g., Orchard, Tampines, CBD, etc."
            )
            self.db.update_lead(sender_id, conversation_step=2)

        elif step == 2:
            # Save location, ask budget
            self.db.update_lead(sender_id, location_pref=text)
            await self.ask_budget(sender_id, lead)

        elif step == 3:
            # Save budget, ask timeline
            await self.parse_budget(sender_id, text)
            await self.ask_timeline(sender_id, lead)

        elif step == 4:
            # Timeline received, ask for contact
            timeline = text.lower()
            self.db.update_lead(sender_id, timeline=timeline)
            await self.ask_contact_info(sender_id, lead)

    async def handle_property_search_postback(self, sender_id: str, lead: Dict, payload: str):
        """Handle property search button clicks"""
        if payload == "PROPERTY_SEARCH":
            self.db.update_lead(
                sender_id,
                conversation_state='property_search',
                conversation_step=0,
                intent='buy'
            )
            await self.handle_property_search(sender_id, lead, "", 0)

    # ========== VALUATION FLOW ==========

    async def handle_valuation_flow(self, sender_id: str, lead: Dict, text: str, step: int):
        """Property valuation request flow"""
        if step == 0:
            self.send_text(
                sender_id,
                "I can help with a free property valuation! 📊\n\n"
                "What's your property address?"
            )
            self.db.update_lead(sender_id, conversation_step=1)

        elif step == 1:
            # Address received
            self.db.update_lead(sender_id, location_pref=text)
            self.send_text(
                sender_id,
                "Got it! What type of property is it?\n\n"
                "E.g., HDB, Condo, Landed"
            )
            self.db.update_lead(sender_id, conversation_step=2)

        elif step == 2:
            # Property type received
            self.db.update_lead(sender_id, property_type=text)
            await self.ask_contact_info(sender_id, lead)

    async def handle_valuation_postback(self, sender_id: str, lead: Dict, payload: str):
        """Handle valuation button clicks"""
        if payload == "VALUATION_REQUEST":
            self.db.update_lead(
                sender_id,
                conversation_state='valuation',
                conversation_step=0,
                intent='sell'
            )
            await self.handle_valuation_flow(sender_id, lead, "", 0)

    # ========== APPOINTMENT FLOW ==========

    async def handle_appointment_flow(self, sender_id: str, lead: Dict, text: str, step: int):
        """Book appointment flow"""
        if step == 0:
            self.send_text(
                sender_id,
                "I'd love to arrange a viewing or consultation!\n\n"
                "When are you available? (e.g., 'This weekend', 'Next Tuesday 3pm')"
            )
            self.db.update_lead(sender_id, conversation_step=1)

        elif step == 1:
            # Preferred time received
            await self.ask_contact_info(sender_id, lead, appointment_time=text)

    async def handle_appointment_postback(self, sender_id: str, lead: Dict, payload: str):
        """Handle appointment button clicks"""
        if payload == "APPOINTMENT_BOOK":
            self.db.update_lead(
                sender_id,
                conversation_state='appointment',
                conversation_step=0
            )
            await self.handle_appointment_flow(sender_id, lead, "", 0)

    # ========== CONTACT COLLECTION ==========

    async def handle_contact_collection(self, sender_id: str, lead: Dict, text: str, step: int):
        """Collect phone and email"""
        if step == 0:
            # Ask phone
            self.send_text(
                sender_id,
                "What's the best number to reach you?"
            )
            self.db.update_lead(sender_id, conversation_step=1)

        elif step == 1:
            # Phone received, ask email
            self.db.update_lead(sender_id, phone=text)
            self.send_text(
                sender_id,
                "And your email address?"
            )
            self.db.update_lead(sender_id, conversation_step=2)

        elif step == 2:
            # Email received, calculate score and create alert
            self.db.update_lead(sender_id, email=text)
            await self.finalize_lead(sender_id, lead)

    async def ask_contact_info(self, sender_id: str, lead: Dict, **kwargs):
        """Transition to contact collection"""
        self.db.update_lead(
            sender_id,
            conversation_state='contact_collection',
            conversation_step=0,
            **kwargs
        )
        await self.handle_contact_collection(sender_id, lead, "", 0)

    async def ask_budget(self, sender_id: str, lead: Dict):
        """Ask budget with quick replies"""
        message = self.templates.budget_selector()
        self.send_message(sender_id, message)

    async def parse_budget(self, sender_id: str, text: str):
        """Parse budget from text or selection"""
        from facebook_bot.config import BUDGET_RANGES

        # Check if matches a budget range key
        for key, (min_val, max_val) in BUDGET_RANGES.items():
            if key.lower() in text.lower():
                self.db.update_lead(
                    sender_id,
                    budget_min=min_val,
                    budget_max=max_val
                )
                return

        # Try to extract numbers
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            budget = int(numbers[0])
            if budget < 10000:  # Assume it's in thousands
                budget *= 1000
            self.db.update_lead(sender_id, budget_min=budget)

    async def ask_timeline(self, sender_id: str, lead: Dict):
        """Ask timeline with quick replies"""
        message = self.templates.timeline_selector()
        self.send_message(sender_id, message)

    async def finalize_lead(self, sender_id: str, lead: Dict):
        """Calculate score and create agent alert if hot lead"""
        # Refresh lead data
        lead = self.db.get_or_create_lead(sender_id)

        # Calculate score
        score = self.db.calculate_lead_score(lead)
        self.db.update_lead(sender_id, lead_score=score)

        # Send confirmation
        self.send_text(
            sender_id,
            f"Perfect! ✅\n\n"
            f"{AGENT_NAME} will get back to you within 24 hours.\n\n"
            f"In the meantime, feel free to ask any questions!"
        )

        # If hot lead, create agent alert
        if score >= 7:
            self.db.create_alert(
                lead_id=lead['id'],
                alert_type='hot_lead',
                alert_message=f"🔥 Hot Lead (Score: {score}/10)\n"
                             f"Name: {lead.get('full_name')}\n"
                             f"Phone: {lead.get('phone')}\n"
                             f"Budget: ${lead.get('budget_min', 0):,}\n"
                             f"Intent: {lead.get('intent')}"
            )

            # Create follow-up sequence
            self.db.create_sequence(lead['id'], 'hot_lead')

        # Return to main menu
        await self.show_main_menu(sender_id, lead)

"""
Database operations for Facebook bot
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from bot_database_postgres import BotDatabase

logger = logging.getLogger(__name__)


class FacebookBotDB:
    """Database handler for Facebook Messenger bot"""

    def __init__(self):
        self.db = BotDatabase()

    # ========== LEAD MANAGEMENT ==========

    def get_or_create_lead(self, facebook_user_id: str, username: str = None,
                           full_name: str = None, source: str = 'messenger') -> Dict:
        """Get existing lead or create new one"""
        lead = self.db.execute_query(
            "SELECT * FROM fb_leads WHERE facebook_user_id = %s",
            (facebook_user_id,),
            fetch='one'
        )

        if not lead:
            self.db.execute_query("""
                INSERT INTO fb_leads (facebook_user_id, username, full_name, source)
                VALUES (%s, %s, %s, %s)
            """, (facebook_user_id, username, full_name, source))

            lead = self.db.execute_query(
                "SELECT * FROM fb_leads WHERE facebook_user_id = %s",
                (facebook_user_id,),
                fetch='one'
            )

        return dict(lead) if lead else None

    def update_lead(self, facebook_user_id: str, **kwargs):
        """Update lead fields"""
        if not kwargs:
            return

        set_clause = ', '.join([f"{k} = %s" for k in kwargs.keys()])
        values = list(kwargs.values()) + [facebook_user_id]

        self.db.execute_query(f"""
            UPDATE fb_leads
            SET {set_clause}, last_contact_at = NOW(), updated_at = NOW()
            WHERE facebook_user_id = %s
        """, tuple(values))

    def calculate_lead_score(self, lead: Dict) -> int:
        """Calculate lead score 0-10"""
        from facebook_bot.config import LEAD_SCORE_WEIGHTS as W

        score = 0

        # Intent
        intent = lead.get('intent', '').lower()
        if intent in ['buy', 'sell', 'invest']:
            score += W['intent_buy']
        elif intent == 'browse':
            score += W['intent_browse']

        # Timeline
        timeline = lead.get('timeline', '')
        if timeline == 'urgent':
            score += W['timeline_urgent']
        elif timeline == '3-6mo':
            score += W['timeline_3_6mo']
        elif timeline == '6-12mo':
            score += W['timeline_6_12mo']

        # Budget
        budget_min = lead.get('budget_min', 0)
        if budget_min >= 1200000:
            score += W['budget_high']
        elif budget_min >= 600000:
            score += W['budget_mid']
        elif budget_min > 0:
            score += W['budget_low']

        # Contact info
        if lead.get('phone'):
            score += W['phone_provided']
        if lead.get('email'):
            score += W['email_provided']

        # Source
        if lead.get('source') == 'messenger':
            score += W['direct_dm']

        return min(score, 10)

    def get_hot_leads(self, threshold: int = 7) -> List[Dict]:
        """Get leads with score >= threshold"""
        results = self.db.execute_query("""
            SELECT * FROM fb_leads
            WHERE lead_score >= %s AND status = 'new'
            ORDER BY lead_score DESC, first_contact_at DESC
            LIMIT 50
        """, (threshold,), fetch='all')
        return [dict(r) for r in results] if results else []

    # ========== MESSAGES ==========

    def save_message(self, lead_id: int, facebook_user_id: str, direction: str,
                     message_text: str = None, message_type: str = 'text',
                     payload: str = None):
        """Save message to conversation history"""
        self.db.execute_query("""
            INSERT INTO fb_messages
                (lead_id, facebook_user_id, direction, message_text, message_type, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (lead_id, facebook_user_id, direction, message_text, message_type, payload))

    def get_conversation_history(self, facebook_user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent conversation history"""
        results = self.db.execute_query("""
            SELECT * FROM fb_messages
            WHERE facebook_user_id = %s
            ORDER BY sent_at DESC
            LIMIT %s
        """, (facebook_user_id, limit), fetch='all')
        return [dict(r) for r in results[::-1]] if results else []

    # ========== COMMENTS ==========

    def has_replied_to_comment(self, comment_id: str) -> bool:
        """Check if already replied to this comment"""
        result = self.db.execute_query(
            "SELECT 1 FROM fb_comment_replies WHERE comment_id = %s",
            (comment_id,),
            fetch='one'
        )
        return result is not None

    def save_comment_reply(self, post_id: str, comment_id: str, commenter_id: str,
                           comment_text: str, reply_text: str, dm_sent: bool = False):
        """Save comment reply to prevent duplicates"""
        self.db.execute_query("""
            INSERT INTO fb_comment_replies
                (post_id, comment_id, commenter_id, comment_text, reply_text, dm_sent)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (comment_id) DO NOTHING
        """, (post_id, comment_id, commenter_id, comment_text, reply_text, dm_sent))

    # ========== SEQUENCES ==========

    def create_sequence(self, lead_id: int, sequence_type: str):
        """Create a follow-up sequence for a lead"""
        self.db.execute_query("""
            INSERT INTO fb_sequences (lead_id, sequence_type, next_send_at)
            VALUES (%s, %s, NOW() + INTERVAL '1 hour')
        """, (lead_id, sequence_type))

    def get_pending_sequences(self) -> List[Dict]:
        """Get sequences ready to send"""
        results = self.db.execute_query("""
            SELECT s.*, l.facebook_user_id, l.full_name, l.lead_score
            FROM fb_sequences s
            JOIN fb_leads l ON s.lead_id = l.id
            WHERE s.next_send_at <= NOW()
              AND s.completed = FALSE
              AND s.paused = FALSE
            ORDER BY s.next_send_at ASC
            LIMIT 50
        """, fetch='all')
        return [dict(r) for r in results] if results else []

    def advance_sequence(self, sequence_id: int, next_delay_hours: int = None):
        """Move sequence to next step"""
        if next_delay_hours:
            self.db.execute_query("""
                UPDATE fb_sequences
                SET current_step = current_step + 1,
                    next_send_at = NOW() + INTERVAL '%s hours'
                WHERE id = %s
            """, (next_delay_hours, sequence_id))
        else:
            # Mark completed
            self.db.execute_query("""
                UPDATE fb_sequences
                SET current_step = current_step + 1, completed = TRUE
                WHERE id = %s
            """, (sequence_id,))

    # ========== AGENT ALERTS ==========

    def create_alert(self, lead_id: int, alert_type: str, alert_message: str):
        """Create agent alert"""
        self.db.execute_query("""
            INSERT INTO fb_agent_alerts (lead_id, alert_type, alert_message)
            VALUES (%s, %s, %s)
        """, (lead_id, alert_type, alert_message))

    def get_pending_alerts(self) -> List[Dict]:
        """Get alerts not yet sent to Telegram"""
        results = self.db.execute_query("""
            SELECT a.*, l.facebook_user_id, l.full_name, l.phone, l.lead_score
            FROM fb_agent_alerts a
            JOIN fb_leads l ON a.lead_id = l.id
            WHERE a.telegram_sent = FALSE
            ORDER BY a.sent_at ASC
            LIMIT 20
        """, fetch='all')
        return [dict(r) for r in results] if results else []

    def mark_alert_sent(self, alert_id: int):
        """Mark alert as sent to Telegram"""
        self.db.execute_query(
            "UPDATE fb_agent_alerts SET telegram_sent = TRUE WHERE id = %s",
            (alert_id,)
        )

    # ========== STATS ==========

    def get_stats(self, days: int = 7) -> Dict:
        """Get bot stats for last N days"""
        since = datetime.now() - timedelta(days=days)

        total_leads = self.db.execute_query("""
            SELECT COUNT(*) as count FROM fb_leads
            WHERE created_at >= %s
        """, (since,), fetch='one')

        hot_leads = self.db.execute_query("""
            SELECT COUNT(*) as count FROM fb_leads
            WHERE created_at >= %s AND lead_score >= 7
        """, (since,), fetch='one')

        avg_score = self.db.execute_query("""
            SELECT AVG(lead_score) as avg FROM fb_leads
            WHERE created_at >= %s
        """, (since,), fetch='one')

        return {
            'total_leads': total_leads['count'] if total_leads else 0,
            'hot_leads': hot_leads['count'] if hot_leads else 0,
            'avg_score': round(avg_score['avg'], 1) if avg_score and avg_score['avg'] else 0,
            'period_days': days
        }

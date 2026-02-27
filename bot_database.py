"""
Database module for Telegram bot
Stores user profiles, credentials, and subscription data
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os


class BotDatabase:
    def __init__(self, db_path='data/telegram_bot.db'):
        """Initialize database"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_active BOOLEAN DEFAULT 0,
                subscription_expires TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT
            )
        ''')

        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                telegram_id INTEGER PRIMARY KEY,
                profile_data TEXT,
                content_strategy TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        # LinkedIn credentials table (encrypted)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS linkedin_credentials (
                telegram_id INTEGER PRIMARY KEY,
                email TEXT,
                encrypted_password BLOB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        # Automation stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                action_type TEXT,
                action_count INTEGER,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        # Promo codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount_percent INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                active BOOLEAN DEFAULT 1
            )
        ''')

        conn.commit()
        conn.close()

    def get_user(self, telegram_id: int) -> dict:
        """Get user by telegram ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM users WHERE telegram_id = ?
        ''', (telegram_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'telegram_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'created_at': row[3],
            'subscription_active': bool(row[4]),
            'subscription_expires': row[5],
            'stripe_customer_id': row[6],
            'stripe_subscription_id': row[7]
        }

    def create_user(self, telegram_id: int, username: str = None, first_name: str = None):
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (telegram_id, username, first_name))

        conn.commit()
        conn.close()

    def save_user_profile(self, telegram_id: int, profile_data: dict, content_strategy: dict):
        """Save user profile and content strategy"""
        self.create_user(telegram_id)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles (telegram_id, profile_data, content_strategy, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (
            telegram_id,
            json.dumps(profile_data),
            json.dumps(content_strategy),
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def get_user_profile(self, telegram_id: int) -> dict:
        """Get user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT profile_data, content_strategy FROM user_profiles
            WHERE telegram_id = ?
        ''', (telegram_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'profile': json.loads(row[0]),
            'content_strategy': json.loads(row[1])
        }

    def save_linkedin_credentials(self, telegram_id: int, email: str, encrypted_password: bytes):
        """Save encrypted LinkedIn credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO linkedin_credentials (telegram_id, email, encrypted_password, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, email, encrypted_password, datetime.now()))

        conn.commit()
        conn.close()

    def get_linkedin_credentials(self, telegram_id: int) -> dict:
        """Get LinkedIn credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT email, encrypted_password FROM linkedin_credentials
            WHERE telegram_id = ?
        ''', (telegram_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'email': row[0],
            'password': row[1]
        }

    def activate_subscription(self, telegram_id: int, stripe_customer_id: str = None,
                            stripe_subscription_id: str = None, days: int = 30):
        """Activate user subscription"""
        from datetime import timedelta

        expires = datetime.now() + timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET subscription_active = 1,
                subscription_expires = ?,
                stripe_customer_id = ?,
                stripe_subscription_id = ?
            WHERE telegram_id = ?
        ''', (expires, stripe_customer_id, stripe_subscription_id, telegram_id))

        conn.commit()
        conn.close()

    def deactivate_subscription(self, telegram_id: int):
        """Deactivate user subscription"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET subscription_active = 0
            WHERE telegram_id = ?
        ''', (telegram_id,))

        conn.commit()
        conn.close()

    def is_subscription_active(self, telegram_id: int) -> bool:
        """Check if user has active subscription"""
        user = self.get_user(telegram_id)
        if not user:
            return False

        if not user['subscription_active']:
            return False

        # Check expiration
        if user['subscription_expires']:
            expires = datetime.fromisoformat(user['subscription_expires'])
            if datetime.now() > expires:
                self.deactivate_subscription(telegram_id)
                return False

        return True

    def log_automation_action(self, telegram_id: int, action_type: str, count: int = 1):
        """Log automation action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO automation_stats (telegram_id, action_type, action_count)
            VALUES (?, ?, ?)
        ''', (telegram_id, action_type, count))

        conn.commit()
        conn.close()

    def get_user_stats(self, telegram_id: int) -> dict:
        """Get user automation statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT action_type, SUM(action_count), MAX(performed_at)
            FROM automation_stats
            WHERE telegram_id = ?
            GROUP BY action_type
        ''', (telegram_id,))

        rows = cursor.fetchall()
        conn.close()

        stats = {
            'posts_created': 0,
            'likes_given': 0,
            'comments_made': 0,
            'connections_sent': 0,
            'last_active': 'Never'
        }

        for row in rows:
            action_type, count, last_time = row
            if action_type == 'post':
                stats['posts_created'] = count
            elif action_type == 'like':
                stats['likes_given'] = count
            elif action_type == 'comment':
                stats['comments_made'] = count
            elif action_type == 'connection':
                stats['connections_sent'] = count

            if last_time:
                stats['last_active'] = last_time

        return stats

    def create_promo_code(self, code: str, discount_percent: int, max_uses: int, days_valid: int):
        """Create a promo code"""
        from datetime import timedelta

        expires = datetime.now() + timedelta(days=days_valid)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO promo_codes (code, discount_percent, max_uses, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (code.upper(), discount_percent, max_uses, expires))

        conn.commit()
        conn.close()

    def validate_promo_code(self, code: str) -> dict:
        """Validate a promo code"""
        # Only two valid codes — all others rejected
        if code.upper() == 'FREE':
            return {
                'valid': True,
                'code': 'FREE',
                'discount_percent': 100,
                'max_uses': 999999,
                'current_uses': 0,
                'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
                'active': True,
                'is_free_bypass': True
            }

        if code.upper() == 'FREETRIAL':
            return {
                'valid': True,
                'code': 'FREETRIAL',
                'discount_percent': 100,
                'max_uses': 999999,
                'current_uses': 0,
                'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
                'active': True,
                'is_freetrial': True
            }

        return {'valid': False, 'reason': 'Invalid code'}

    def use_promo_code(self, code: str):
        """Mark promo code as used"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE promo_codes
            SET current_uses = current_uses + 1
            WHERE code = ?
        ''', (code.upper(),))

        conn.commit()
        conn.close()

"""
PostgreSQL Database module for Telegram bot
Replaces SQLite with PostgreSQL RDS
Includes connection pooling and support for all 13 tables
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extras import RealDictCursor, Json
import json
from datetime import datetime, timedelta, date
import os
from typing import Optional, Dict, List, Any, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotDatabase:
    """PostgreSQL database with connection pooling"""

    def __init__(self,
                 host: str = None,
                 port: int = None,
                 database: str = None,
                 user: str = None,
                 password: str = None,
                 min_connections: int = 2,
                 max_connections: int = 10):
        """
        Initialize PostgreSQL database with connection pool

        Environment variables:
        - DATABASE_HOST (default: localhost)
        - DATABASE_PORT (default: 5432)
        - DATABASE_NAME (default: linkedin_bot)
        - DATABASE_USER (default: postgres)
        - DATABASE_PASSWORD (required for production)
        """
        self.host = host or os.getenv('DATABASE_HOST', 'localhost')
        self.port = port or int(os.getenv('DATABASE_PORT', 5432))
        self.database = database or os.getenv('DATABASE_NAME', 'linkedin_bot')
        self.user = user or os.getenv('DATABASE_USER', 'postgres')
        self.password = password or os.getenv('DATABASE_PASSWORD', '')

        try:
            # Create threaded connection pool
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            logger.info(f"PostgreSQL connection pool created: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    def get_connection(self):
        """Get connection from pool"""
        return self.connection_pool.getconn()

    def return_connection(self, conn):
        """Return connection to pool"""
        self.connection_pool.putconn(conn)

    def execute_query(self, query: str, params: Tuple = None, fetch: str = None):
        """
        Execute query with automatic connection management

        Args:
            query: SQL query with %s placeholders
            params: Query parameters tuple
            fetch: 'one', 'all', or None

        Returns:
            Query result or None
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())

                if fetch == 'one':
                    result = cursor.fetchone()
                elif fetch == 'all':
                    result = cursor.fetchall()
                else:
                    result = None

                conn.commit()
                return result
        except Exception as e:
            conn.rollback()
            logger.error(f"Query error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        finally:
            self.return_connection(conn)

    def close(self):
        """Close all connections in pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Connection pool closed")

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        return self.execute_query(
            "SELECT * FROM users WHERE telegram_id = %s",
            (telegram_id,),
            fetch='one'
        )

    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> bool:
        """Create new user"""
        try:
            self.execute_query("""
                INSERT INTO users (telegram_id, username, first_name, last_seen)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_seen = CURRENT_TIMESTAMP
            """, (telegram_id, username, first_name))
            return True
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return False

    def update_last_seen(self, telegram_id: int):
        """Update user's last seen timestamp"""
        self.execute_query(
            "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE telegram_id = %s",
            (telegram_id,)
        )

    # =========================================================================
    # USER PROFILES
    # =========================================================================

    def save_user_profile(self, telegram_id: int, profile_data: dict, content_strategy: dict = None) -> bool:
        """
        Save user profile and content strategy

        Args:
            telegram_id: User's Telegram ID
            profile_data: Dict with industry, skills, career_goals, tone, interests (all arrays)
            content_strategy: Dict with content_themes, posting_frequency, optimal_times, content_goals
        """
        try:
            # Ensure user exists
            self.create_user(telegram_id)

            # Save user profile (arrays)
            self.execute_query("""
                INSERT INTO user_profiles (telegram_id, industry, skills, career_goals, tone, interests)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    industry = EXCLUDED.industry,
                    skills = EXCLUDED.skills,
                    career_goals = EXCLUDED.career_goals,
                    tone = EXCLUDED.tone,
                    interests = EXCLUDED.interests,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                telegram_id,
                profile_data.get('industry', []),
                profile_data.get('skills', []),
                profile_data.get('career_goals', []),
                profile_data.get('tone', []),
                profile_data.get('interests', [])
            ))

            # Save content strategy if provided
            if content_strategy:
                # Convert time strings to time objects
                optimal_times = content_strategy.get('optimal_times', ['09:00', '13:00', '17:00'])
                if optimal_times and isinstance(optimal_times[0], str):
                    # Already strings, PostgreSQL will handle conversion
                    pass

                self.execute_query("""
                    INSERT INTO content_strategies (telegram_id, content_themes, posting_frequency, optimal_times, content_goals)
                    VALUES (%s, %s, %s, %s::TIME[], %s)
                    ON CONFLICT (telegram_id) DO UPDATE SET
                        content_themes = EXCLUDED.content_themes,
                        posting_frequency = EXCLUDED.posting_frequency,
                        optimal_times = EXCLUDED.optimal_times,
                        content_goals = EXCLUDED.content_goals,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    telegram_id,
                    content_strategy.get('content_themes', []),
                    content_strategy.get('posting_frequency', 'daily'),
                    optimal_times,
                    content_strategy.get('content_goals', [])
                ))

            return True
        except Exception as e:
            logger.error(f"Error saving user profile {telegram_id}: {e}")
            return False

    def get_user_profile(self, telegram_id: int) -> Optional[Dict]:
        """
        Get user profile and content strategy

        Returns combined dict with profile_data and content_strategy
        """
        try:
            # Get profile data
            profile = self.execute_query(
                "SELECT * FROM user_profiles WHERE telegram_id = %s",
                (telegram_id,),
                fetch='one'
            )

            # Get content strategy
            strategy = self.execute_query(
                "SELECT * FROM content_strategies WHERE telegram_id = %s",
                (telegram_id,),
                fetch='one'
            )

            if not profile:
                return None

            # Convert to format expected by existing code
            result = {
                'telegram_id': telegram_id,
                'profile_data': {
                    'industry': profile.get('industry', []),
                    'skills': profile.get('skills', []),
                    'career_goals': profile.get('career_goals', []),
                    'tone': profile.get('tone', []),
                    'interests': profile.get('interests', [])
                }
            }

            if strategy:
                # Convert time objects to strings
                optimal_times = strategy.get('optimal_times', [])
                if optimal_times and not isinstance(optimal_times[0], str):
                    optimal_times = [str(t) for t in optimal_times]

                result['content_strategy'] = {
                    'content_themes': strategy.get('content_themes', []),
                    'posting_frequency': strategy.get('posting_frequency', 'daily'),
                    'optimal_times': optimal_times,
                    'content_goals': strategy.get('content_goals', [])
                }

            return result
        except Exception as e:
            logger.error(f"Error getting user profile {telegram_id}: {e}")
            return None

    # =========================================================================
    # LINKEDIN CREDENTIALS
    # =========================================================================

    def save_linkedin_credentials(self, telegram_id: int, email: str, encrypted_password: bytes) -> bool:
        """Save encrypted LinkedIn credentials"""
        try:
            # Ensure user exists (foreign key constraint)
            self.create_user(telegram_id)

            self.execute_query("""
                INSERT INTO linkedin_credentials (telegram_id, email, encrypted_password)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    encrypted_password = EXCLUDED.encrypted_password,
                    updated_at = CURRENT_TIMESTAMP
            """, (telegram_id, email, psycopg2.Binary(encrypted_password)))
            return True
        except Exception as e:
            logger.error(f"Error saving credentials for {telegram_id}: {e}")
            return False

    def get_linkedin_credentials(self, telegram_id: int) -> Optional[Dict]:
        """Get encrypted LinkedIn credentials"""
        result = self.execute_query(
            "SELECT email, encrypted_password FROM linkedin_credentials WHERE telegram_id = %s",
            (telegram_id,),
            fetch='one'
        )

        if result:
            return {
                'email': result['email'],
                'encrypted_password': bytes(result['encrypted_password'])  # Convert memoryview to bytes
            }
        return None

    def update_login_stats(self, telegram_id: int, success: bool):
        """Update login attempt statistics"""
        if success:
            self.execute_query("""
                UPDATE linkedin_credentials SET
                    last_login_attempt = CURRENT_TIMESTAMP,
                    login_success_count = login_success_count + 1
                WHERE telegram_id = %s
            """, (telegram_id,))
        else:
            self.execute_query("""
                UPDATE linkedin_credentials SET
                    last_login_attempt = CURRENT_TIMESTAMP,
                    login_failure_count = login_failure_count + 1
                WHERE telegram_id = %s
            """, (telegram_id,))

    # =========================================================================
    # SUBSCRIPTION MANAGEMENT
    # =========================================================================

    def activate_subscription(self, telegram_id: int, stripe_customer_id: str = None,
                            stripe_subscription_id: str = None, days: int = 30) -> bool:
        """Activate user subscription"""
        try:
            expiration = datetime.now() + timedelta(days=days)

            self.execute_query("""
                UPDATE users SET
                    subscription_active = TRUE,
                    subscription_expires = %s,
                    stripe_customer_id = COALESCE(%s, stripe_customer_id),
                    stripe_subscription_id = COALESCE(%s, stripe_subscription_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = %s
            """, (expiration, stripe_customer_id, stripe_subscription_id, telegram_id))
            return True
        except Exception as e:
            logger.error(f"Error activating subscription for {telegram_id}: {e}")
            return False

    def deactivate_subscription(self, telegram_id: int) -> bool:
        """Deactivate user subscription"""
        try:
            self.execute_query(
                "UPDATE users SET subscription_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = %s",
                (telegram_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error deactivating subscription for {telegram_id}: {e}")
            return False

    def is_subscription_active(self, telegram_id: int) -> bool:
        """Check if user has active subscription"""
        result = self.execute_query("""
            SELECT subscription_active, subscription_expires
            FROM users WHERE telegram_id = %s
        """, (telegram_id,), fetch='one')

        if not result:
            return False

        # Auto-deactivate if expired
        if result['subscription_active'] and result['subscription_expires']:
            from datetime import timezone
            if result['subscription_expires'] < datetime.now(timezone.utc):
                self.deactivate_subscription(telegram_id)
                return False

        return result.get('subscription_active', False)

    # =========================================================================
    # AUTOMATION STATS
    # =========================================================================

    def log_automation_action(self, telegram_id: int, action_type: str,
                             action_count: int = 1, session_id: str = None,
                             metadata: dict = None) -> bool:
        """Log automation action"""
        try:
            self.execute_query("""
                INSERT INTO automation_stats (telegram_id, action_type, action_count, session_id, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (telegram_id, action_type, action_count, session_id,
                  Json(metadata) if metadata else None))
            return True
        except Exception as e:
            logger.error(f"Error logging action for {telegram_id}: {e}")
            return False

    def get_user_stats(self, telegram_id: int) -> Dict:
        """Get user automation statistics"""
        result = self.execute_query("""
            SELECT
                COALESCE(SUM(CASE WHEN action_type = 'post' THEN action_count END), 0) as posts_created,
                COALESCE(SUM(CASE WHEN action_type = 'like' THEN action_count END), 0) as likes_given,
                COALESCE(SUM(CASE WHEN action_type = 'comment' THEN action_count END), 0) as comments_made,
                COALESCE(SUM(CASE WHEN action_type = 'connection' THEN action_count END), 0) as connections_sent,
                MAX(performed_at) as last_active
            FROM automation_stats
            WHERE telegram_id = %s
        """, (telegram_id,), fetch='one')

        if result:
            return {
                'posts_created': int(result['posts_created']),
                'likes_given': int(result['likes_given']),
                'comments_made': int(result['comments_made']),
                'connections_sent': int(result['connections_sent']),
                'last_active': result['last_active'].isoformat() if result['last_active'] else None
            }

        return {
            'posts_created': 0,
            'likes_given': 0,
            'comments_made': 0,
            'connections_sent': 0,
            'last_active': None
        }

    # =========================================================================
    # PROMO CODES
    # =========================================================================

    def create_promo_code(self, code: str, discount_percent: int,
                         max_uses: int, days_valid: int = 30) -> bool:
        """Create promo code"""
        try:
            expires_at = datetime.now() + timedelta(days=days_valid)

            self.execute_query("""
                INSERT INTO promo_codes (code, discount_percent, max_uses, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (code.upper(), discount_percent, max_uses, expires_at))
            return True
        except Exception as e:
            logger.error(f"Error creating promo code {code}: {e}")
            return False

    def validate_promo_code(self, code: str) -> Optional[Dict]:
        """Validate promo code"""
        # Only two valid codes — all others rejected
        if code.upper() == 'FREE':
            return {
                'code': 'FREE',
                'discount_percent': 100,
                'max_uses': 999999,
                'current_uses': 0,
                'expires_at': datetime.now() + timedelta(days=365),
                'active': True,
                'is_free_bypass': True
            }

        if code.upper() == 'FREETRIAL':
            return {
                'code': 'FREETRIAL',
                'discount_percent': 100,
                'max_uses': 999999,
                'current_uses': 0,
                'expires_at': datetime.now() + timedelta(days=365),
                'active': True,
                'is_freetrial': True
            }

        return None

    def use_promo_code(self, code: str) -> bool:
        """Increment promo code usage"""
        try:
            self.execute_query(
                "UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code = %s",
                (code.upper(),)
            )
            return True
        except Exception as e:
            logger.error(f"Error using promo code {code}: {e}")
            return False

    # =========================================================================
    # ENGAGEMENT TRACKING
    # =========================================================================

    def mark_post_engaged(self, telegram_id: int, post_id: str,
                         engagement_type: str = 'like', post_content: str = None) -> bool:
        """Mark post as engaged (prevent duplicate engagement)"""
        try:
            self.execute_query("""
                INSERT INTO engaged_posts (telegram_id, post_id, engagement_type, post_content)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (telegram_id, post_id) DO UPDATE SET
                    engagement_type = EXCLUDED.engagement_type,
                    engaged_at = CURRENT_TIMESTAMP
            """, (telegram_id, post_id, engagement_type, post_content))
            return True
        except Exception as e:
            logger.error(f"Error marking post engaged: {e}")
            return False

    def has_engaged_post(self, telegram_id: int, post_id: str) -> bool:
        """Check if already engaged with post"""
        result = self.execute_query(
            "SELECT 1 FROM engaged_posts WHERE telegram_id = %s AND post_id = %s",
            (telegram_id, post_id),
            fetch='one'
        )
        return result is not None

    def mark_post_commented(self, telegram_id: int, post_id: str,
                           comment_text: str = None, ai_generated: bool = False) -> bool:
        """Mark post as commented (prevent duplicate comments)"""
        try:
            self.execute_query("""
                INSERT INTO commented_posts (telegram_id, post_id, comment_text, ai_generated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (telegram_id, post_id) DO NOTHING
            """, (telegram_id, post_id, comment_text, ai_generated))
            return True
        except Exception as e:
            logger.error(f"Error marking post commented: {e}")
            return False

    def has_commented_post(self, telegram_id: int, post_id: str) -> bool:
        """Check if already commented on post"""
        result = self.execute_query(
            "SELECT 1 FROM commented_posts WHERE telegram_id = %s AND post_id = %s",
            (telegram_id, post_id),
            fetch='one'
        )
        return result is not None

    # =========================================================================
    # SAFETY / RATE LIMITING
    # =========================================================================

    def increment_safety_count(self, telegram_id: int, action_type: str, count: int = 1):
        """Increment daily action count"""
        self.execute_query("""
            INSERT INTO safety_counts (telegram_id, date, action_type, count)
            VALUES (%s, CURRENT_DATE, %s, %s)
            ON CONFLICT (telegram_id, date, action_type) DO UPDATE SET
                count = safety_counts.count + EXCLUDED.count
        """, (telegram_id, action_type, count))

    def get_daily_count(self, telegram_id: int, action_type: str) -> int:
        """Get daily action count"""
        result = self.execute_query("""
            SELECT count FROM safety_counts
            WHERE telegram_id = %s AND date = CURRENT_DATE AND action_type = %s
        """, (telegram_id, action_type), fetch='one')

        return result['count'] if result else 0

    def reset_daily_counts(self, telegram_id: int):
        """Reset daily counts (called at midnight)"""
        self.execute_query(
            "DELETE FROM safety_counts WHERE telegram_id = %s AND date < CURRENT_DATE",
            (telegram_id,)
        )

    # =========================================================================
    # JOB SEARCH SCANNER
    # =========================================================================

    def get_job_search_config(self, telegram_id: int) -> Optional[Dict]:
        """Get job search configuration for a user"""
        return self.execute_query(
            "SELECT * FROM job_seeking_configs WHERE telegram_id = %s",
            (telegram_id,),
            fetch='one'
        )

    def save_job_search_config(self, telegram_id: int, roles: list = None,
                               locations: list = None, keywords: list = None,
                               enabled: bool = True) -> bool:
        """Create or update job search configuration"""
        try:
            self.execute_query("""
                INSERT INTO job_seeking_configs
                    (telegram_id, target_roles, target_locations, scan_keywords,
                     notification_enabled, enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    target_roles = COALESCE(EXCLUDED.target_roles, job_seeking_configs.target_roles),
                    target_locations = COALESCE(EXCLUDED.target_locations, job_seeking_configs.target_locations),
                    scan_keywords = COALESCE(EXCLUDED.scan_keywords, job_seeking_configs.scan_keywords),
                    notification_enabled = EXCLUDED.notification_enabled,
                    enabled = EXCLUDED.enabled,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                telegram_id,
                roles or [],
                locations or [],
                keywords or [],
                enabled,
                enabled,
            ))
            return True
        except Exception as e:
            logger.error(f"Error saving job search config for {telegram_id}: {e}")
            return False

    def save_resume_keywords(self, telegram_id: int, keywords: list) -> bool:
        """Save keywords extracted from user's resume"""
        try:
            self.execute_query("""
                INSERT INTO job_seeking_configs (telegram_id, resume_keywords)
                VALUES (%s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    resume_keywords = EXCLUDED.resume_keywords,
                    updated_at = CURRENT_TIMESTAMP
            """, (telegram_id, keywords or []))
            return True
        except Exception as e:
            logger.error(f"Error saving resume keywords for {telegram_id}: {e}")
            return False

    def get_seen_job_ids(self, telegram_id: int) -> set:
        """Get set of job IDs already seen by this user (last 14 days)"""
        results = self.execute_query("""
            SELECT job_id FROM seen_jobs
            WHERE telegram_id = %s
              AND seen_at > NOW() - INTERVAL '14 days'
        """, (telegram_id,), fetch='all')
        return {row['job_id'] for row in results} if results else set()

    def save_seen_job(self, telegram_id: int, job: dict) -> bool:
        """Save a job as seen (prevents duplicate notifications)"""
        try:
            self.execute_query("""
                INSERT INTO seen_jobs (telegram_id, job_id, job_title, company, location, job_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id, job_id) DO NOTHING
            """, (
                telegram_id,
                job.get('job_id'),
                job.get('title', '')[:500],
                job.get('company', '')[:255],
                job.get('location', '')[:255],
                job.get('job_url', ''),
            ))
            return True
        except Exception as e:
            logger.error(f"Error saving seen job for {telegram_id}: {e}")
            return False

    def update_last_scan(self, telegram_id: int):
        """Update the last scan timestamp for a user"""
        self.execute_query("""
            UPDATE job_seeking_configs
            SET last_scan_at = CURRENT_TIMESTAMP
            WHERE telegram_id = %s
        """, (telegram_id,))

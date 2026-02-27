"""
Analytics Module
Tracks bot performance and provides insights for optimization
"""

import sqlite3
import utils
from datetime import datetime, timedelta
import json

class Analytics:
    def __init__(self, db_path='data/analytics.db'):
        """
        Initialize Analytics Module

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            utils.ensure_directory('data')

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Posts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    theme TEXT,
                    posted_at TIMESTAMP,
                    is_ai_generated BOOLEAN,
                    estimated_reach INTEGER DEFAULT 0
                )
            ''')

            # Engagements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT,
                    post_id TEXT,
                    author_name TEXT,
                    relevance_score REAL,
                    engaged_at TIMESTAMP,
                    was_ai_filtered BOOLEAN
                )
            ''')

            # Connections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_url TEXT,
                    name TEXT,
                    title TEXT,
                    is_recruiter BOOLEAN,
                    is_hiring_manager BOOLEAN,
                    connection_value REAL,
                    requested_at TIMESTAMP,
                    accepted BOOLEAN DEFAULT NULL,
                    accepted_at TIMESTAMP
                )
            ''')

            # Daily stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    posts_created INTEGER DEFAULT 0,
                    likes_given INTEGER DEFAULT 0,
                    comments_made INTEGER DEFAULT 0,
                    connections_requested INTEGER DEFAULT 0,
                    connections_accepted INTEGER DEFAULT 0,
                    profile_views INTEGER DEFAULT 0,
                    follower_count INTEGER DEFAULT 0
                )
            ''')

            conn.commit()
            conn.close()

            utils.log("Analytics database initialized", "SUCCESS")

        except Exception as e:
            utils.log(f"Error initializing analytics database: {str(e)}", "ERROR")

    def log_post(self, content, theme="", is_ai_generated=False):
        """
        Log a posted content

        Args:
            content: Post content
            theme: Theme of the post
            is_ai_generated: Whether post was AI-generated

        Returns:
            int: Post ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO posts (content, theme, posted_at, is_ai_generated)
                VALUES (?, ?, ?, ?)
            ''', (content[:500], theme, datetime.now(), is_ai_generated))

            post_id = cursor.lastrowid

            # Update daily stats
            self._update_daily_stat('posts_created', 1)

            conn.commit()
            conn.close()

            utils.log(f"Post logged (ID: {post_id})")
            return post_id

        except Exception as e:
            utils.log(f"Error logging post: {str(e)}", "ERROR")
            return None

    def log_engagement(self, action_type, post_id="", author_name="", relevance_score=0.0, was_ai_filtered=False):
        """
        Log an engagement action

        Args:
            action_type: Type of action (like, comment, share)
            post_id: ID of the post engaged with
            author_name: Name of post author
            relevance_score: AI relevance score
            was_ai_filtered: Whether AI filtering was used
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO engagements (action_type, post_id, author_name, relevance_score, engaged_at, was_ai_filtered)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (action_type, post_id, author_name, relevance_score, datetime.now(), was_ai_filtered))

            # Update daily stats
            if action_type == 'like':
                self._update_daily_stat('likes_given', 1)
            elif action_type == 'comment':
                self._update_daily_stat('comments_made', 1)

            conn.commit()
            conn.close()

            utils.log(f"Engagement logged: {action_type}")

        except Exception as e:
            utils.log(f"Error logging engagement: {str(e)}", "ERROR")

    def log_connection(self, profile_url, name, title, is_recruiter=False, is_hiring_manager=False, connection_value=0.0):
        """
        Log a connection request

        Args:
            profile_url: Profile URL
            name: Person's name
            title: Professional title
            is_recruiter: Whether person is a recruiter
            is_hiring_manager: Whether person is a hiring manager
            connection_value: Connection value score
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO connections (profile_url, name, title, is_recruiter, is_hiring_manager, connection_value, requested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (profile_url, name, title, is_recruiter, is_hiring_manager, connection_value, datetime.now()))

            # Update daily stats
            self._update_daily_stat('connections_requested', 1)

            conn.commit()
            conn.close()

            utils.log(f"Connection logged: {name}")

        except Exception as e:
            utils.log(f"Error logging connection: {str(e)}", "ERROR")

    def _update_daily_stat(self, stat_name, increment=1):
        """Update a daily statistic"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            today = datetime.now().date()

            # Check if entry exists for today
            cursor.execute('SELECT id FROM daily_stats WHERE date = ?', (today,))
            row = cursor.fetchone()

            if row:
                # Update existing
                cursor.execute(f'''
                    UPDATE daily_stats
                    SET {stat_name} = {stat_name} + ?
                    WHERE date = ?
                ''', (increment, today))
            else:
                # Create new entry
                cursor.execute(f'''
                    INSERT INTO daily_stats (date, {stat_name})
                    VALUES (?, ?)
                ''', (today, increment))

            conn.commit()
            conn.close()

        except Exception as e:
            utils.log(f"Error updating daily stat: {str(e)}", "ERROR")

    def get_daily_summary(self, date=None):
        """
        Get summary for a specific date

        Args:
            date: Date to get summary for (default: today)

        Returns:
            dict: Daily statistics
        """
        if not date:
            date = datetime.now().date()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (date,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return {
                    'date': row[1],
                    'posts_created': row[2],
                    'likes_given': row[3],
                    'comments_made': row[4],
                    'connections_requested': row[5],
                    'connections_accepted': row[6],
                    'profile_views': row[7],
                    'follower_count': row[8]
                }
            else:
                return {
                    'date': str(date),
                    'posts_created': 0,
                    'likes_given': 0,
                    'comments_made': 0,
                    'connections_requested': 0,
                    'connections_accepted': 0,
                    'profile_views': 0,
                    'follower_count': 0
                }

        except Exception as e:
            utils.log(f"Error getting daily summary: {str(e)}", "ERROR")
            return {}

    def get_weekly_summary(self):
        """
        Get summary for the last 7 days

        Returns:
            dict: Weekly statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            week_ago = datetime.now().date() - timedelta(days=7)

            cursor.execute('''
                SELECT
                    SUM(posts_created), SUM(likes_given), SUM(comments_made),
                    SUM(connections_requested), SUM(connections_accepted)
                FROM daily_stats
                WHERE date >= ?
            ''', (week_ago,))

            row = cursor.fetchone()
            conn.close()

            return {
                'period': 'Last 7 days',
                'posts_created': row[0] or 0,
                'likes_given': row[1] or 0,
                'comments_made': row[2] or 0,
                'connections_requested': row[3] or 0,
                'connections_accepted': row[4] or 0,
                'connection_acceptance_rate': f"{(row[4] / row[3] * 100) if row[3] > 0 else 0:.1f}%"
            }

        except Exception as e:
            utils.log(f"Error getting weekly summary: {str(e)}", "ERROR")
            return {}

    def get_ai_effectiveness(self):
        """
        Analyze effectiveness of AI features

        Returns:
            dict: AI effectiveness metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # AI-generated posts vs manual
            cursor.execute('SELECT COUNT(*) FROM posts WHERE is_ai_generated = 1')
            ai_posts = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM posts WHERE is_ai_generated = 0')
            manual_posts = cursor.fetchone()[0]

            # AI-filtered engagements
            cursor.execute('SELECT AVG(relevance_score) FROM engagements WHERE was_ai_filtered = 1')
            avg_relevance = cursor.fetchone()[0] or 0

            # Recruiter connections
            cursor.execute('SELECT COUNT(*) FROM connections WHERE is_recruiter = 1')
            recruiter_connections = cursor.fetchone()[0]

            conn.close()

            return {
                'ai_generated_posts': ai_posts,
                'manual_posts': manual_posts,
                'average_relevance_score': f"{avg_relevance:.2f}",
                'recruiter_connections': recruiter_connections,
                'ai_usage_percentage': f"{(ai_posts / (ai_posts + manual_posts) * 100) if (ai_posts + manual_posts) > 0 else 0:.1f}%"
            }

        except Exception as e:
            utils.log(f"Error calculating AI effectiveness: {str(e)}", "ERROR")
            return {}

    def print_dashboard(self):
        """Print a formatted analytics dashboard"""
        print("\n" + "="*60)
        print("LinkedIn Automation Bot - Analytics Dashboard")
        print("="*60)

        # Today's summary
        today_stats = self.get_daily_summary()
        print("\nToday's Activity:")
        print(f"  Posts Created: {today_stats.get('posts_created', 0)}")
        print(f"  Likes Given: {today_stats.get('likes_given', 0)}")
        print(f"  Comments Made: {today_stats.get('comments_made', 0)}")
        print(f"  Connection Requests: {today_stats.get('connections_requested', 0)}")

        # Weekly summary
        weekly_stats = self.get_weekly_summary()
        print("\nWeekly Summary:")
        for key, value in weekly_stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

        # AI effectiveness
        ai_stats = self.get_ai_effectiveness()
        print("\nAI Features Performance:")
        for key, value in ai_stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

        print("="*60 + "\n")

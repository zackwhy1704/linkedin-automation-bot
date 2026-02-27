"""
Relevance Scorer Module
Uses AI to score LinkedIn posts for relevance to user's interests and goals
"""

import utils
import json
import os

ENGAGED_POSTS_FILE = 'data/engaged_posts.json'
COMMENTED_POSTS_FILE = 'data/commented_posts.json'

class RelevanceScorer:
    def __init__(self, ai_service, config_file='data/engagement_config.json'):
        """
        Initialize Relevance Scorer

        Args:
            ai_service: AIService instance for making AI calls
            config_file: Path to engagement configuration file
        """
        self.ai_service = ai_service
        self.config = self._load_config(config_file)
        self.relevance_threshold = self.config.get('relevance_threshold', 0.6)
        self.keywords_to_engage = self.config.get('keywords_to_engage', [])

        # Track engaged posts to avoid duplicates — persisted to disk
        self.engaged_posts = self._load_engaged_posts()

        # Track commented posts separately as additional safeguard
        self.commented_posts = self._load_commented_posts()

    def _load_config(self, config_file):
        """Load configuration from file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            utils.log(f"Config file not found: {config_file}", "WARNING")
            return {}
        except json.JSONDecodeError:
            utils.log(f"Invalid JSON in config: {config_file}", "ERROR")
            return {}

    def _load_engaged_posts(self):
        """Load engaged posts from disk"""
        try:
            with open(ENGAGED_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                posts = set(data.get('engaged_post_ids', []))
                utils.log(f"Loaded {len(posts)} previously engaged posts from disk")
                return posts
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def _save_engaged_posts(self):
        """Save engaged posts to disk so they persist across restarts"""
        try:
            os.makedirs(os.path.dirname(ENGAGED_POSTS_FILE), exist_ok=True)
            with open(ENGAGED_POSTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'engaged_post_ids': list(self.engaged_posts)}, f, indent=2)
        except Exception as e:
            utils.log(f"Error saving engaged posts: {str(e)}", "ERROR")

    def _load_commented_posts(self):
        """Load commented posts from disk"""
        try:
            with open(COMMENTED_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                posts = set(data.get('commented_post_ids', []))
                utils.log(f"Loaded {len(posts)} previously commented posts from disk")
                return posts
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def _save_commented_posts(self):
        """Save commented posts to disk so they persist across restarts"""
        try:
            os.makedirs(os.path.dirname(COMMENTED_POSTS_FILE), exist_ok=True)
            with open(COMMENTED_POSTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'commented_post_ids': list(self.commented_posts)}, f, indent=2)
        except Exception as e:
            utils.log(f"Error saving commented posts: {str(e)}", "ERROR")

    def score_post(self, post_content, author_name="", author_title="", user_profile=None):
        """
        Score a post's relevance for engagement

        Args:
            post_content: The text content of the post
            author_name: Name of the post author
            author_title: Professional title of the author
            user_profile: User's profile information (from content_strategy.json)

        Returns:
            float: Relevance score between 0.0 and 1.0
        """
        if not post_content or len(post_content.strip()) == 0:
            utils.log("Empty post content, skipping", "WARNING")
            return 0.0

        # Use AI service to analyze relevance
        try:
            score = self.ai_service.analyze_post_relevance(
                post_content=post_content,
                author_name=author_name,
                author_title=author_title,
                user_profile=user_profile
            )

            utils.log(f"Post relevance score: {score:.2f} (threshold: {self.relevance_threshold})")
            return score

        except Exception as e:
            utils.log(f"Error scoring post relevance: {str(e)}", "ERROR")
            # Fallback to simple keyword matching
            return self._simple_relevance_score(post_content)

    def _simple_relevance_score(self, post_content):
        """
        Simple keyword-based relevance scoring as fallback

        Args:
            post_content: The post content to analyze

        Returns:
            float: Simple relevance score
        """
        if not post_content:
            return 0.0

        post_lower = post_content.lower()
        score = 0.0

        # Check for configured keywords
        for keyword in self.keywords_to_engage:
            if keyword.lower() in post_lower:
                score += 0.2

        # Limit max score from fallback method
        return min(score, 0.7)

    def should_engage(self, post_id, post_content, author_name="", author_title="", user_profile=None):
        """
        Determine if bot should engage with this post

        Args:
            post_id: Unique identifier for the post
            post_content: The post content
            author_name: Author's name
            author_title: Author's title
            user_profile: User's profile info

        Returns:
            tuple: (should_engage: bool, score: float, reason: str)
        """
        # Check if already engaged with this post
        if post_id in self.engaged_posts:
            return False, 0.0, "Already engaged with this post"

        # Score the post
        score = self.score_post(post_content, author_name, author_title, user_profile)

        # Determine if we should engage
        if score >= self.relevance_threshold:
            self.engaged_posts.add(post_id)
            self._save_engaged_posts()
            return True, score, f"Relevant post (score: {score:.2f})"
        else:
            return False, score, f"Below relevance threshold (score: {score:.2f})"

    def analyze_author_value(self, author_title, author_company=""):
        """
        Analyze the value of engaging with this author

        Args:
            author_title: Professional title of the author
            author_company: Company the author works for

        Returns:
            dict: Analysis with is_recruiter, is_hiring_manager, value_score
        """
        profile_data = {
            'name': '',
            'title': author_title,
            'company': author_company,
            'bio': '',
            'context': ''
        }

        try:
            analysis = self.ai_service.analyze_profile(profile_data)
            return analysis
        except Exception as e:
            utils.log(f"Error analyzing author: {str(e)}", "ERROR")
            return {
                'is_recruiter': False,
                'is_hiring_manager': False,
                'is_relevant': False,
                'connection_value': 0.0
            }

    def get_engagement_stats(self):
        """Get statistics about engagement filtering"""
        return {
            'total_posts_engaged': len(self.engaged_posts),
            'relevance_threshold': self.relevance_threshold,
            'keywords_tracked': len(self.keywords_to_engage)
        }

    def has_commented_on_post(self, post_id):
        """
        Check if we've already commented on this post

        Args:
            post_id: Unique post identifier

        Returns:
            bool: True if already commented
        """
        return post_id in self.commented_posts

    def mark_post_commented(self, post_id):
        """
        Mark a post as commented

        Args:
            post_id: Unique post identifier
        """
        self.commented_posts.add(post_id)
        self._save_commented_posts()
        utils.log(f"Post marked as commented: {post_id[:16]}...")

    def reset_engaged_posts(self):
        """Reset the list of engaged posts (call daily or weekly)"""
        count = len(self.engaged_posts)
        self.engaged_posts.clear()
        self._save_engaged_posts()
        utils.log(f"Reset engaged posts tracker ({count} posts cleared)")

    def reset_commented_posts(self):
        """Reset the list of commented posts"""
        count = len(self.commented_posts)
        self.commented_posts.clear()
        self._save_commented_posts()
        utils.log(f"Reset commented posts tracker ({count} posts cleared)")

"""
Safety Manager Module
Prevents account bans by enforcing rate limits and safe usage patterns
"""

import utils
import json
from datetime import datetime, timedelta
from collections import defaultdict

class SafetyManager:
    def __init__(self, config_file='data/job_seeking_config.json'):
        """
        Initialize Safety Manager

        Args:
            config_file: Path to configuration with safety limits
        """
        self.config = self._load_config(config_file)

        # Default safety limits (conservative to avoid detection)
        self.daily_limits = {
            'connection_requests': self.config.get('outreach_limits', {}).get('connection_requests_per_day', 15),
            'messages': self.config.get('outreach_limits', {}).get('messages_per_day', 10),
            'likes': 50,
            'comments': 10,
            'profile_views': 30,
            'searches': 20
        }

        # Track actions
        self.action_counts = defaultdict(int)
        self.last_reset_date = datetime.now().date()
        self.last_action_time = {}
        self.cooldown_until = None

        # Load persisted counts if available
        self._load_daily_counts()

    def _load_config(self, config_file):
        """Load configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _load_daily_counts(self):
        """Load action counts from previous session"""
        try:
            with open('data/safety_counts.json', 'r') as f:
                data = json.load(f)
                saved_date = datetime.fromisoformat(data['date']).date()

                # Only load if it's the same day
                if saved_date == datetime.now().date():
                    self.action_counts = defaultdict(int, data['counts'])
                    utils.log("Loaded existing daily action counts")
        except:
            pass

    def _save_daily_counts(self):
        """Save action counts to file"""
        try:
            utils.ensure_directory('data')
            data = {
                'date': datetime.now().isoformat(),
                'counts': dict(self.action_counts)
            }
            with open('data/safety_counts.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            utils.log(f"Error saving safety counts: {str(e)}", "WARNING")

    def _reset_daily_counts(self):
        """Reset counters if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            utils.log("Resetting daily action counters", "INFO")
            self.action_counts = defaultdict(int)
            self.last_reset_date = current_date
            self._save_daily_counts()

    def check_action_allowed(self, action_type):
        """
        Check if an action is allowed based on daily limits

        Args:
            action_type: Type of action (e.g., 'connection_requests', 'likes')

        Returns:
            tuple: (is_allowed: bool, reason: str)
        """
        self._reset_daily_counts()

        # Check if in cooldown
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).seconds // 60
            return False, f"In cooldown for {remaining} more minutes"

        # Check daily limit for this action
        if action_type not in self.daily_limits:
            return True, "No limit set for this action"

        limit = self.daily_limits[action_type]
        current_count = self.action_counts[action_type]

        if current_count >= limit:
            return False, f"Daily limit reached for {action_type} ({current_count}/{limit})"

        # Check if approaching limit (warning at 80%)
        if current_count >= limit * 0.8:
            utils.log(f"Warning: Approaching daily limit for {action_type} ({current_count}/{limit})", "WARNING")

        return True, "Action allowed"

    def log_action(self, action_type):
        """
        Log that an action was performed

        Args:
            action_type: Type of action performed
        """
        self._reset_daily_counts()

        self.action_counts[action_type] += 1
        self.last_action_time[action_type] = datetime.now()

        utils.log(f"Action logged: {action_type} ({self.action_counts[action_type]}/{self.daily_limits.get(action_type, 'unlimited')})")

        # Save counts after each action
        self._save_daily_counts()

        # Check if we should trigger cooldown (too many actions too quickly)
        self._check_activity_pattern()

    def _check_activity_pattern(self):
        """Check if activity pattern looks suspicious and trigger cooldown if needed"""
        # Get actions in last 5 minutes
        now = datetime.now()
        recent_threshold = now - timedelta(minutes=5)

        recent_actions = sum(
            1 for timestamp in self.last_action_time.values()
            if timestamp > recent_threshold
        )

        # If more than 10 actions in 5 minutes, trigger cooldown
        if recent_actions > 10:
            self.cooldown_until = now + timedelta(minutes=15)
            utils.log("Suspicious activity pattern detected. Triggering 15-minute cooldown.", "WARNING")

    def enforce_cooldown(self, minutes=5):
        """
        Manually trigger a cooldown period

        Args:
            minutes: Number of minutes for cooldown
        """
        self.cooldown_until = datetime.now() + timedelta(minutes=minutes)
        utils.log(f"Cooldown enforced for {minutes} minutes", "INFO")

    def get_remaining_actions(self, action_type):
        """
        Get number of remaining actions for the day

        Args:
            action_type: Type of action

        Returns:
            int: Remaining actions allowed
        """
        self._reset_daily_counts()

        if action_type not in self.daily_limits:
            return float('inf')

        limit = self.daily_limits[action_type]
        current = self.action_counts[action_type]
        return max(0, limit - current)

    def get_daily_summary(self):
        """
        Get summary of daily actions

        Returns:
            dict: Summary of action counts and limits
        """
        self._reset_daily_counts()

        summary = {}
        for action_type, limit in self.daily_limits.items():
            count = self.action_counts[action_type]
            summary[action_type] = {
                'count': count,
                'limit': limit,
                'remaining': limit - count,
                'percentage_used': (count / limit * 100) if limit > 0 else 0
            }

        return summary

    def is_safe_to_continue(self):
        """
        Check if it's safe to continue automation

        Returns:
            tuple: (is_safe: bool, reason: str)
        """
        # Check cooldown
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).seconds // 60
            return False, f"In cooldown ({remaining} minutes remaining)"

        # Check if any critical limits are reached
        critical_actions = ['connection_requests', 'messages']
        for action in critical_actions:
            if action in self.daily_limits:
                if self.action_counts[action] >= self.daily_limits[action]:
                    return False, f"Daily limit reached for {action}"

        # Check total activity level
        total_actions = sum(self.action_counts.values())
        if total_actions > 100:  # More than 100 total actions per day is risky
            return False, "Total daily action limit approaching (100+ actions)"

        return True, "Safe to continue"

    def get_recommended_delay(self, action_type):
        """
        Get recommended delay before next action

        Args:
            action_type: Type of action

        Returns:
            tuple: (min_seconds, max_seconds)
        """
        # Base delays (in seconds)
        delays = {
            'connection_requests': (30, 60),  # 30-60 seconds between connections
            'messages': (20, 40),  # 20-40 seconds between messages
            'likes': (2, 5),  # 2-5 seconds between likes
            'comments': (5, 10),  # 5-10 seconds between comments
            'searches': (10, 20),  # 10-20 seconds between searches
            'profile_views': (3, 7)  # 3-7 seconds between views
        }

        return delays.get(action_type, (2, 5))

    def reset_for_new_day(self):
        """Manually reset counters (for testing or new day)"""
        self.action_counts = defaultdict(int)
        self.last_reset_date = datetime.now().date()
        self.cooldown_until = None
        self._save_daily_counts()
        utils.log("Safety manager reset for new day", "SUCCESS")

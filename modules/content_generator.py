"""
Content Generator Module
Generates AI-powered LinkedIn posts to showcase expertise and attract opportunities
"""

import utils
import json
import random
from datetime import datetime, timedelta

class ContentGenerator:
    def __init__(self, ai_service, config_file='data/content_strategy.json'):
        """
        Initialize Content Generator

        Args:
            ai_service: AIService instance for generating content
            config_file: Path to content strategy configuration
        """
        self.ai_service = ai_service
        self.config = self._load_config(config_file)
        self.user_profile = self.config.get('user_profile', {})
        self.content_themes = self.config.get('content_themes', [])
        self.content_goals = self.config.get('content_goals', [])

        # Track generated content to avoid repetition
        self.recent_themes = []
        self.max_recent_themes = 7  # Don't repeat themes within a week

    def _load_config(self, config_file):
        """Load content strategy configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            utils.log(f"Config file not found: {config_file}, using defaults", "WARNING")
            return self._get_default_config()
        except json.JSONDecodeError:
            utils.log(f"Invalid JSON in config: {config_file}", "ERROR")
            return self._get_default_config()

    def _get_default_config(self):
        """Get default configuration"""
        return {
            'user_profile': {
                'industry': 'software development',
                'skills': ['Python', 'automation'],
                'career_goals': 'senior developer role',
                'tone': 'professional yet approachable'
            },
            'content_themes': [
                'technical tutorials',
                'career insights',
                'project showcases',
                'industry trends'
            ],
            'content_goals': [
                'demonstrate expertise',
                'attract recruiters'
            ]
        }

    def generate_post(self, theme=None, include_hashtags=True):
        """
        Generate an AI-powered LinkedIn post

        Args:
            theme: Specific theme/topic (optional, will pick randomly if not provided)
            include_hashtags: Whether to include hashtags

        Returns:
            str: Generated post content
        """
        # Select theme
        if not theme:
            theme = self._select_theme()

        utils.log(f"Generating post about: {theme}")

        try:
            # Generate post using AI
            post_content = self.ai_service.generate_post(
                theme=theme,
                user_profile=self.user_profile
            )

            # Track this theme to avoid repetition
            self.recent_themes.append(theme)
            if len(self.recent_themes) > self.max_recent_themes:
                self.recent_themes.pop(0)

            utils.log("Successfully generated AI post", "SUCCESS")
            return post_content

        except Exception as e:
            utils.log(f"Error generating post: {str(e)}", "ERROR")
            return self._generate_fallback_post(theme)

    def _select_theme(self):
        """
        Select a theme for the next post (avoiding recent themes)

        Returns:
            str: Selected theme
        """
        # Filter out recently used themes
        available_themes = [
            theme for theme in self.content_themes
            if theme not in self.recent_themes
        ]

        # If all themes were used recently, reset
        if not available_themes:
            available_themes = self.content_themes
            self.recent_themes.clear()

        theme = random.choice(available_themes)
        utils.log(f"Selected theme: {theme}")
        return theme

    def _generate_fallback_post(self, theme):
        """Generate enhanced template-based post as fallback with story-telling format"""
        # Story hooks
        hooks = [
            f"I recently had a conversation that completely changed how I think about {theme}. 🤔",
            f"Here's something I wish someone had told me earlier about {theme}... 💡",
            f"Last week, I was reminded why {theme} matters more than ever in today's landscape. 🚀",
        ]

        # Key insights with emojis
        insights = [
            f"💎 {theme.title()} isn't just about what you know — it's about how you apply it in real-world scenarios.",
            f"🎯 Success comes from combining technical skills with genuine curiosity and continuous learning.",
            f"🔥 The most valuable skill isn't always technical — it's the ability to adapt and evolve.",
            f"⚡ Innovation happens at the intersection of knowledge and creative problem-solving.",
        ]

        # Action points
        actions = [
            "📌 Focus on building genuine connections, not just collecting contacts",
            "📌 Share your knowledge freely — what you give comes back multiplied",
            "📌 Ask better questions instead of just seeking quick answers",
            "📌 Stay curious and never stop learning from those around you",
        ]

        # Engagement questions
        questions = [
            "What's been your biggest learning moment this year? 👇",
            "How do you approach this in your field? I'd love to hear your thoughts! 💬",
            "What strategies have worked for you? Drop your insights below! 🗣️",
            "What's your take on this? Share your perspective! 🤝",
        ]

        # Build enhanced post
        hook = random.choice(hooks)
        selected_insights = random.sample(insights, 3)
        selected_actions = random.sample(actions, 3)
        question = random.choice(questions)

        post = (
            f"{hook}\n\n"
            f"Here's what I've discovered:\n\n"
            f"{selected_insights[0]}\n\n"
            f"{selected_insights[1]}\n\n"
            f"{selected_insights[2]}\n\n"
            f"Three things that have helped me:\n\n"
            f"{selected_actions[0]}\n"
            f"{selected_actions[1]}\n"
            f"{selected_actions[2]}\n\n"
            f"{question}\n\n"
            f"#TechCommunity #CareerGrowth #Learning #ProfessionalDevelopment"
        )

        return post

    def generate_weekly_content_plan(self):
        """
        Generate content ideas for a full week

        Returns:
            list: List of dicts with theme, suggested_time, and content
        """
        utils.log("Generating weekly content plan...")

        optimal_times = self.config.get('optimal_times', ['09:00', '13:00', '17:00'])
        posting_days = 7  # Daily posting

        content_plan = []

        for day in range(posting_days):
            theme = self._select_theme()
            post_time = random.choice(optimal_times)

            # Calculate posting datetime
            post_date = datetime.now() + timedelta(days=day)
            post_datetime = post_date.replace(
                hour=int(post_time.split(':')[0]),
                minute=int(post_time.split(':')[1]),
                second=0
            )

            content_plan.append({
                'day': day + 1,
                'theme': theme,
                'suggested_time': post_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'content_preview': f"AI-generated post about {theme}"
            })

        utils.log(f"Generated {len(content_plan)} content ideas for the week", "SUCCESS")
        return content_plan

    def generate_and_preview(self, theme=None):
        """
        Generate a post and return it for preview before posting

        Args:
            theme: Optional theme

        Returns:
            dict: Post info with content, theme, and metadata
        """
        theme = theme or self._select_theme()
        content = self.generate_post(theme=theme)

        return {
            'theme': theme,
            'content': content,
            'length': len(content),
            'estimated_engagement': self._estimate_engagement(content),
            'generated_at': datetime.now().isoformat()
        }

    def _estimate_engagement(self, content):
        """
        Estimate potential engagement for a post (simple heuristic)

        Args:
            content: Post content

        Returns:
            str: Engagement estimate (low/medium/high)
        """
        # Simple heuristics
        has_question = '?' in content
        has_hashtags = '#' in content
        length = len(content)

        score = 0
        if has_question:
            score += 2  # Questions encourage engagement
        if has_hashtags:
            score += 1
        if 150 <= length <= 300:
            score += 2  # Optimal length

        if score >= 4:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"

    def optimize_hashtags(self, post_content):
        """
        Generate optimized hashtags for a post

        Args:
            post_content: The post content

        Returns:
            list: List of recommended hashtags
        """
        # Extract industry and skills
        industry = self.user_profile.get('industry', 'software development')

        # Use AI to suggest hashtags if available
        if self.ai_service:
            try:
                # This would use the hashtag optimization prompt
                # For now, use intelligent defaults based on content
                pass
            except:
                pass

        # Default hashtag strategy
        hashtags = []

        # Industry hashtags
        if 'software' in industry.lower() or 'developer' in industry.lower():
            hashtags.extend(['#SoftwareDevelopment', '#Programming', '#TechCommunity'])

        # Career-focused hashtags (for job seeking)
        hashtags.extend(['#CareerGrowth', '#TechCareer'])

        # Content-specific hashtags based on keywords
        content_lower = post_content.lower()
        if 'python' in content_lower:
            hashtags.append('#Python')
        if 'javascript' in content_lower or 'js' in content_lower:
            hashtags.append('#JavaScript')
        if 'ai' in content_lower or 'artificial intelligence' in content_lower:
            hashtags.append('#AI')
        if 'automation' in content_lower:
            hashtags.append('#Automation')
        if 'career' in content_lower or 'job' in content_lower:
            hashtags.append('#JobSearch')

        # Return top 5 unique hashtags
        unique_hashtags = list(dict.fromkeys(hashtags))[:5]
        return unique_hashtags

    def generate_job_seeking_post(self):
        """
        Generate a post specifically designed to attract recruiters

        Returns:
            str: Job-seeking optimized post
        """
        utils.log("Generating job-seeking post...")

        # Themes that showcase expertise and attract recruiters
        job_seeking_themes = [
            "recent technical project and skills demonstrated",
            "problem-solving approach and technical expertise",
            "learning journey and growth mindset",
            "contributions to open source or community",
            "technical skills and experience highlights"
        ]

        theme = random.choice(job_seeking_themes)

        # Add context for AI to generate recruiter-friendly content
        enhanced_theme = f"{theme} (showcase expertise to attract recruiters and hiring managers)"

        post = self.generate_post(theme=enhanced_theme)

        # Ensure it has job-seeking hashtags
        if '#OpenToWork' not in post and '#JobSearch' not in post:
            post += " #OpenToWork #Hiring"

        return post

    def schedule_content(self, days=7, video_folder=None, schedule_file='data/scheduled_content.json'):
        """
        Pre-generate AI content and schedule it for future posting.
        Optionally pairs each post with a video from a folder.

        Args:
            days: Number of days to schedule content for
            video_folder: Path to folder containing video files to attach
            schedule_file: Path to save the scheduled content JSON

        Returns:
            list: List of scheduled content items
        """
        import os
        import glob

        utils.log(f"Generating scheduled content for {days} days...")

        optimal_times = self.config.get('optimal_times', ['09:00', '13:00', '17:00'])
        scheduled_items = []

        # Load existing scheduled content if any
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                next_id = max((item.get('id', 0) for item in existing), default=0) + 1
        except (FileNotFoundError, json.JSONDecodeError):
            existing = []
            next_id = 1

        # Collect video files if folder provided
        video_files = []
        if video_folder and os.path.isdir(video_folder):
            video_extensions = ['*.mp4', '*.mov', '*.avi', '*.wmv', '*.mkv', '*.webm']
            for ext in video_extensions:
                video_files.extend(glob.glob(os.path.join(video_folder, ext)))
            video_files.sort()
            utils.log(f"Found {len(video_files)} video(s) in {video_folder}")

        video_index = 0

        for day in range(days):
            theme = self._select_theme()
            post_time = random.choice(optimal_times)

            # Calculate posting datetime
            post_date = datetime.now() + timedelta(days=day + 1)
            post_datetime = post_date.replace(
                hour=int(post_time.split(':')[0]),
                minute=int(post_time.split(':')[1]),
                second=0
            )

            # Generate the actual post content
            utils.log(f"Generating content for Day {day + 1}: {theme}")
            content = self.generate_post(theme=theme)

            if not content:
                utils.log(f"Failed to generate content for Day {day + 1}, skipping", "WARNING")
                continue

            # Assign a video if available
            media_path = None
            media_type = None
            if video_files and video_index < len(video_files):
                media_path = os.path.abspath(video_files[video_index])
                media_type = "video"
                video_index += 1
            elif video_files and video_index >= len(video_files):
                # Loop back to first video if we have more days than videos
                video_index = 0
                media_path = os.path.abspath(video_files[video_index])
                media_type = "video"
                video_index += 1

            item = {
                'id': next_id,
                'content': content,
                'theme': theme,
                'schedule_time': post_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'media': media_path,
                'media_type': media_type,
                'posted': False,
                'generated_at': datetime.now().isoformat()
            }

            scheduled_items.append(item)
            next_id += 1
            utils.log(f"  Scheduled: {post_datetime.strftime('%Y-%m-%d %H:%M')} | {theme[:40]}..." +
                      (f" + video" if media_path else ""))

        # Save all scheduled content
        all_items = existing + scheduled_items
        try:
            os.makedirs(os.path.dirname(schedule_file), exist_ok=True)
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(all_items, f, indent=2, ensure_ascii=False)
            utils.log(f"Saved {len(scheduled_items)} scheduled posts to {schedule_file}", "SUCCESS")
        except Exception as e:
            utils.log(f"Error saving schedule: {str(e)}", "ERROR")

        return scheduled_items

    def preview_scheduled(self, schedule_file='data/scheduled_content.json'):
        """
        Preview all scheduled content

        Args:
            schedule_file: Path to scheduled content JSON

        Returns:
            list: List of pending scheduled items
        """
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                items = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            utils.log("No scheduled content found", "WARNING")
            return []

        pending = [item for item in items if not item.get('posted', False)]
        utils.log(f"\n{'='*60}")
        utils.log(f"Scheduled Content ({len(pending)} pending)")
        utils.log(f"{'='*60}")

        for item in pending:
            media_info = f" + {item.get('media_type', 'none')}" if item.get('media') else ""
            print(f"\n[{item['id']}] {item['schedule_time']}{media_info}")
            print(f"    Theme: {item.get('theme', 'N/A')}")
            print(f"    Preview: {item['content'][:80]}...")
            print(f"    {'─'*50}")

        return pending

    def get_content_stats(self):
        """Get statistics about content generation"""
        return {
            'recent_themes': self.recent_themes,
            'available_themes': len(self.content_themes),
            'themes_exhausted': len(self.recent_themes) >= len(self.content_themes),
            'user_industry': self.user_profile.get('industry'),
            'posting_goals': len(self.content_goals)
        }

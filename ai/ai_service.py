"""
AI Service for LinkedIn Automation Bot
Integrates with Anthropic Claude API for intelligent content generation and analysis
"""

import os
import json
from anthropic import Anthropic
from ai.prompts import get_prompt, get_post_generation_prompt, get_comment_style, IMPROVED_TEMPLATE_COMMENTS
import utils
import random
import time
from datetime import datetime, timedelta

class AIService:
    def __init__(self, config_file='data/engagement_config.json'):
        """Initialize AI Service with Anthropic Claude"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key:
            utils.log("Warning: ANTHROPIC_API_KEY not found in environment. AI features will use fallback templates.", "WARNING")
            self.client = None
        else:
            try:
                self.client = Anthropic(api_key=self.api_key)
                utils.log("AI Service initialized with Claude API", "SUCCESS")
            except Exception as e:
                utils.log(f"Error initializing Claude API: {str(e)}", "ERROR")
                self.client = None

        # Load configuration
        self.config = self._load_config(config_file)
        self.ai_config = self.config.get('ai_config', {})
        self.model = self.ai_config.get('model', 'claude-haiku-4-5-20251001')
        self.temperature = self.ai_config.get('temperature', 0.7)
        self.max_tokens = self.ai_config.get('max_tokens', 500)

        # API call tracking
        self.daily_api_calls = 0
        self.max_daily_calls = self.ai_config.get('max_daily_calls', 100)
        self.last_reset_date = datetime.now().date()

        # Cache for profile analyses (24 hour TTL)
        self.profile_cache = {}

        # Track recent comments to avoid repetition
        self.recent_comments = []
        self.max_recent_comments = 20

    def _load_config(self, config_file):
        """Load engagement configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            utils.log(f"Config file not found: {config_file}, using defaults", "WARNING")
            return {}
        except json.JSONDecodeError:
            utils.log(f"Invalid JSON in config file: {config_file}", "ERROR")
            return {}

    def _reset_daily_counter(self):
        """Reset daily API call counter if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_api_calls = 0
            self.last_reset_date = current_date
            utils.log("Daily API call counter reset", "INFO")

    def _check_api_limit(self):
        """Check if we've reached daily API limit"""
        self._reset_daily_counter()
        if self.daily_api_calls >= self.max_daily_calls:
            utils.log(f"Daily API limit reached ({self.max_daily_calls} calls). Using fallback.", "WARNING")
            return False
        return True

    def _call_claude_api(self, prompt, max_tokens=None):
        """
        Make a call to Claude API

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate (default from config)

        Returns:
            str: Generated text or None if error
        """
        if not self.client:
            return None

        if not self._check_api_limit():
            return None

        try:
            self.daily_api_calls += 1

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            utils.log(f"AI API call successful (calls today: {self.daily_api_calls}/{self.max_daily_calls})")
            return response_text.strip()

        except Exception as e:
            utils.log(f"Error calling Claude API: {str(e)}", "ERROR")
            return None

    def generate_post(self, theme, user_profile=None):
        """
        Generate a LinkedIn post using AI

        Args:
            theme: Topic or theme for the post
            user_profile: Dict with industry, skills, career_goals, tone

        Returns:
            str: Generated post content with hashtags
        """
        if not user_profile:
            # Load from content_strategy.json if available
            try:
                with open('data/content_strategy.json', 'r') as f:
                    config = json.load(f)
                    user_profile = config.get('user_profile', {})
            except:
                # Use defaults
                user_profile = {
                    'industry': 'software development',
                    'skills': 'Python, automation, AI',
                    'career_goals': 'senior developer role',
                    'tone': 'professional yet approachable'
                }

        # Use random format selector for variety across posts
        prompt = get_post_generation_prompt(
            industry=user_profile.get('industry', 'software development'),
            skills=', '.join(user_profile.get('skills', [])) if isinstance(user_profile.get('skills'), list) else user_profile.get('skills', 'Python'),
            career_goals=user_profile.get('career_goals', 'career growth'),
            tone=user_profile.get('tone', 'professional'),
            theme=theme
        )

        post_content = self._call_claude_api(prompt, max_tokens=400)

        if post_content:
            utils.log(f"Generated AI post about: {theme}")
            return post_content
        else:
            # Fallback to template
            utils.log("AI generation failed, using template fallback", "WARNING")
            return self._generate_template_post(theme)

    def _generate_template_post(self, theme):
        """Fallback template-based post generation with enhanced story-telling format"""
        # Story hooks
        hooks = [
            f"I recently had a conversation that completely changed how I think about {theme}. 🤔",
            f"Here's something I wish someone had told me earlier about {theme}... 💡",
            f"Last week, I was reminded why {theme} matters more than ever. 🚀",
        ]

        # Key insights with emojis
        insights = [
            f"💎 {theme.title()} isn't just about what you know — it's about how you apply it in real-world scenarios.",
            f"🎯 Success comes from combining technical skills with genuine curiosity and continuous learning.",
            f"⚡ Innovation happens at the intersection of knowledge and creative problem-solving.",
        ]

        # Action points
        actions = [
            "📌 Focus on building genuine connections, not just collecting contacts",
            "📌 Share your knowledge freely — what you give comes back multiplied",
            "📌 Stay curious and never stop learning from those around you",
        ]

        # Engagement questions
        questions = [
            "What's been your biggest learning moment this year? 👇",
            "How do you approach this in your field? I'd love to hear your thoughts! 💬",
            "What's your take on this? Share your perspective! 🤝",
        ]

        # Build enhanced post
        hook = random.choice(hooks)
        selected_insights = random.sample(insights, 2)
        selected_actions = random.sample(actions, 2)
        question = random.choice(questions)

        post = (
            f"{hook}\n\n"
            f"Here's what I've discovered:\n\n"
            f"{selected_insights[0]}\n\n"
            f"{selected_insights[1]}\n\n"
            f"Two things that have helped me:\n\n"
            f"{selected_actions[0]}\n"
            f"{selected_actions[1]}\n\n"
            f"{question}\n\n"
            f"#CareerGrowth #TechIndustry #Learning #ProfessionalDevelopment"
        )

        return post

    def analyze_post_relevance(self, post_content, author_name="", author_title="", user_profile=None):
        """
        Analyze how relevant a post is for the user

        Args:
            post_content: The content of the post
            author_name: Name of the post author
            author_title: Professional title of the author
            user_profile: Dict with user's profile information

        Returns:
            float: Relevance score between 0.0 and 1.0
        """
        if not user_profile:
            try:
                with open('data/content_strategy.json', 'r') as f:
                    config = json.load(f)
                    user_profile = config.get('user_profile', {})
            except:
                user_profile = {
                    'industry': 'software development',
                    'skills': ['Python', 'automation'],
                    'career_goals': 'career growth',
                    'interests': ['technology', 'programming']
                }

        prompt = get_prompt(
            'relevance_scoring',
            industry=user_profile.get('industry', 'software development'),
            skills=', '.join(user_profile.get('skills', [])) if isinstance(user_profile.get('skills'), list) else str(user_profile.get('skills', 'Python')),
            career_goals=user_profile.get('career_goals', 'career growth'),
            interests=', '.join(user_profile.get('interests', [])) if isinstance(user_profile.get('interests'), list) else str(user_profile.get('interests', 'technology')),
            post_content=post_content[:500],  # Limit length to save tokens
            author_name=author_name,
            author_title=author_title
        )

        result = self._call_claude_api(prompt, max_tokens=10)

        if result:
            try:
                # Extract number from response
                score = float(result.strip())
                score = max(0.0, min(1.0, score))  # Clamp between 0 and 1
                utils.log(f"Post relevance score: {score:.2f}")
                return score
            except ValueError:
                utils.log(f"Could not parse relevance score: {result}", "WARNING")
                return self._fallback_relevance_score(post_content, user_profile)
        else:
            return self._fallback_relevance_score(post_content, user_profile)

    def _fallback_relevance_score(self, post_content, user_profile):
        """Simple keyword-based relevance scoring as fallback"""
        score = 0.0
        post_lower = post_content.lower()

        # Check for user's skills/interests
        skills = user_profile.get('skills', [])
        if isinstance(skills, str):
            skills = [skills]

        for skill in skills:
            if skill.lower() in post_lower:
                score += 0.3

        # Check for industry keywords
        industry_keywords = ['developer', 'programming', 'software', 'engineer', 'code', 'tech']
        for keyword in industry_keywords:
            if keyword in post_lower:
                score += 0.1

        return min(score, 0.7)  # Max 0.7 for fallback scoring

    def generate_contextual_comment(self, post_content, author_name="", author_title="", user_profile=None):
        """
        Generate a contextual comment for a post

        Args:
            post_content: Content of the post to comment on
            author_name: Name of the post author
            author_title: Title of the post author
            user_profile: User's profile information

        Returns:
            str: Generated comment
        """
        if not user_profile:
            try:
                with open('data/content_strategy.json', 'r') as f:
                    config = json.load(f)
                    user_profile = config.get('user_profile', {})
            except:
                user_profile = {
                    'industry': 'software development',
                    'skills': ['Python'],
                    'tone': 'professional yet approachable'
                }

        # Pick a random comment style for variety
        comment_style = get_comment_style()

        # Build instruction to avoid repeating recent comments
        recent_comments_instruction = ""
        if self.recent_comments:
            recent_list = "\n".join(f"- {c}" for c in self.recent_comments[-5:])
            recent_comments_instruction = f"DO NOT repeat or closely resemble these recent comments you already posted:\n{recent_list}\nWrite something clearly different in structure and wording."

        prompt = get_prompt(
            'comment_generation',
            post_content=post_content[:500],
            author_name=author_name,
            author_title=author_title,
            industry=user_profile.get('industry', 'software development'),
            skills=', '.join(user_profile.get('skills', [])) if isinstance(user_profile.get('skills'), list) else str(user_profile.get('skills', 'Python')),
            tone=user_profile.get('tone', 'professional'),
            comment_style=comment_style,
            recent_comments_instruction=recent_comments_instruction
        )

        comment = self._call_claude_api(prompt, max_tokens=100)

        if comment:
            # Track this comment to avoid repetition
            self.recent_comments.append(comment)
            if len(self.recent_comments) > self.max_recent_comments:
                self.recent_comments.pop(0)
            utils.log("Generated contextual comment")
            return comment
        else:
            # Fallback to improved templates
            return self._generate_template_comment(post_content)

    def _generate_template_comment(self, post_content):
        """Generate comment using improved templates as fallback"""
        # Try to extract a key topic from the post
        post_lower = post_content.lower()
        topics = ['python', 'javascript', 'automation', 'ai', 'development', 'career', 'technology', 'software']

        found_topic = None
        for topic in topics:
            if topic in post_lower:
                found_topic = topic
                break

        if found_topic:
            template = random.choice(IMPROVED_TEMPLATE_COMMENTS)
            comment = template.format(topic=found_topic, industry='tech')
        else:
            # Generic but improved comments
            comments = [
                "Thanks for sharing this perspective! Really valuable insights.",
                "This is a great breakdown. I appreciate you taking the time to share this.",
                "Interesting approach! I've been thinking about this topic recently too.",
                "Really resonates with my experience. Thanks for articulating this so well!",
            ]
            comment = random.choice(comments)

        return comment

    def analyze_profile(self, profile_data, user_job_search_config=None):
        """
        Analyze a LinkedIn profile to determine if person is valuable for networking

        Args:
            profile_data: Dict with name, title, company, bio, etc.
            user_job_search_config: User's job search configuration

        Returns:
            dict: Analysis results with is_recruiter, is_hiring_manager, connection_value, etc.
        """
        # Check cache first
        cache_key = f"{profile_data.get('name')}_{profile_data.get('title')}"
        if cache_key in self.profile_cache:
            cache_entry = self.profile_cache[cache_key]
            if datetime.now() - cache_entry['timestamp'] < timedelta(hours=24):
                utils.log("Using cached profile analysis")
                return cache_entry['data']

        if not user_job_search_config:
            try:
                with open('data/job_seeking_config.json', 'r') as f:
                    user_job_search_config = json.load(f)
            except:
                user_job_search_config = {
                    'target_roles': ['Software Engineer'],
                    'target_industries': ['technology']
                }

        prompt = get_prompt(
            'profile_analysis',
            name=profile_data.get('name', 'Unknown'),
            title=profile_data.get('title', ''),
            company=profile_data.get('company', ''),
            bio=profile_data.get('bio', '')[:300],
            context=profile_data.get('context', ''),
            target_roles=', '.join(user_job_search_config.get('target_roles', ['Software Engineer'])),
            target_industries=', '.join(user_job_search_config.get('target_companies', ['tech'])),
            user_industry='software development'
        )

        result = self._call_claude_api(prompt, max_tokens=150)

        if result:
            analysis = self._parse_profile_analysis(result)
        else:
            analysis = self._fallback_profile_analysis(profile_data)

        # Cache the result
        self.profile_cache[cache_key] = {
            'timestamp': datetime.now(),
            'data': analysis
        }

        return analysis

    def _parse_profile_analysis(self, result):
        """Parse the profile analysis result"""
        analysis = {
            'is_recruiter': False,
            'is_hiring_manager': False,
            'is_relevant': False,
            'connection_value': 0.0,
            'reasoning': ''
        }

        lines = result.lower().split('\n')
        for line in lines:
            if 'is_recruiter:' in line:
                analysis['is_recruiter'] = 'yes' in line
            elif 'is_hiring_manager:' in line:
                analysis['is_hiring_manager'] = 'yes' in line
            elif 'is_relevant:' in line:
                analysis['is_relevant'] = 'yes' in line
            elif 'connection_value:' in line:
                try:
                    value = line.split(':')[1].strip()
                    analysis['connection_value'] = float(value)
                except:
                    pass
            elif 'reasoning:' in line:
                analysis['reasoning'] = line.split(':', 1)[1].strip()

        return analysis

    def _fallback_profile_analysis(self, profile_data):
        """Simple keyword-based profile analysis as fallback"""
        title = profile_data.get('title', '').lower()
        bio = profile_data.get('bio', '').lower()
        combined = f"{title} {bio}"

        recruiter_keywords = ['recruiter', 'talent acquisition', 'hiring', 'hr', 'headhunter']
        hiring_keywords = ['director', 'manager', 'head of', 'vp', 'cto', 'lead', 'chief']

        is_recruiter = any(keyword in combined for keyword in recruiter_keywords)
        is_hiring_manager = any(keyword in combined for keyword in hiring_keywords)

        connection_value = 0.0
        if is_recruiter:
            connection_value = 0.9
        elif is_hiring_manager:
            connection_value = 0.7
        elif 'engineer' in combined or 'developer' in combined:
            connection_value = 0.5

        return {
            'is_recruiter': is_recruiter,
            'is_hiring_manager': is_hiring_manager,
            'is_relevant': is_recruiter or is_hiring_manager or connection_value > 0.4,
            'connection_value': connection_value,
            'reasoning': 'Keyword-based analysis'
        }

    def generate_personalized_message(self, recipient_profile, sender_profile, purpose="networking"):
        """
        Generate personalized connection request or message

        Args:
            recipient_profile: Dict with recipient's info
            sender_profile: Dict with sender's info
            purpose: Purpose of message (networking, job_inquiry, etc.)

        Returns:
            str: Personalized message
        """
        prompt = get_prompt(
            'message_generation',
            recipient_name=recipient_profile.get('name', 'there'),
            recipient_title=recipient_profile.get('title', 'professional'),
            recipient_company=recipient_profile.get('company', 'your company'),
            context=recipient_profile.get('context', ''),
            sender_industry=sender_profile.get('industry', 'software development'),
            sender_skills=', '.join(sender_profile.get('skills', [])) if isinstance(sender_profile.get('skills'), list) else str(sender_profile.get('skills', 'Python')),
            sender_goals=sender_profile.get('career_goals', 'professional growth'),
            purpose=purpose
        )

        message = self._call_claude_api(prompt, max_tokens=150)

        if message:
            utils.log("Generated personalized message")
            # Ensure it's within LinkedIn's character limit
            if len(message) > 300:
                message = message[:297] + "..."
            return message
        else:
            return self._generate_template_message(recipient_profile, purpose)

    def _generate_template_message(self, recipient_profile, purpose):
        """Fallback template message generation"""
        name = recipient_profile.get('name', 'there')
        title = recipient_profile.get('title', 'professional')

        templates = [
            f"Hi {name}, I came across your profile and was impressed by your work as {title}. I'd love to connect and learn from your experience!",
            f"Hello {name}, Your background in {title} caught my attention. I'm interested in connecting with professionals in this space. Looking forward to connecting!",
            f"Hi {name}, I noticed we share similar professional interests. Would love to connect and potentially exchange insights about {title}!",
        ]

        message = random.choice(templates)
        if len(message) > 300:
            message = message[:297] + "..."
        return message

    def get_api_usage_stats(self):
        """Get current API usage statistics"""
        return {
            'daily_calls': self.daily_api_calls,
            'max_daily_calls': self.max_daily_calls,
            'calls_remaining': self.max_daily_calls - self.daily_api_calls,
            'date': str(self.last_reset_date)
        }

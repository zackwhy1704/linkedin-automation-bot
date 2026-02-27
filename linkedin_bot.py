from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from modules.login import LinkedInLogin
from modules.posting import LinkedInPosting
from modules.auto_reply import LinkedInAutoReply
from modules.engagement import LinkedInEngagement
from modules.messaging import LinkedInMessaging
# AI-Powered Modules
from ai.ai_service import AIService
from modules.content_generator import ContentGenerator
from modules.relevance_scorer import RelevanceScorer
from modules.profile_analyzer import ProfileAnalyzer
from modules.safety_manager import SafetyManager
from modules.analytics import Analytics
from modules.job_search import LinkedInJobSearch
import utils
import os
import json
import random

class LinkedInBot:
    def __init__(self, email, password, headless=False, enable_ai=True, driver=None):
        """
        Initialize LinkedIn Bot

        Args:
            email: LinkedIn email
            password: LinkedIn password
            headless: Run browser in headless mode
            enable_ai: Enable AI-powered features (requires ANTHROPIC_API_KEY)
            driver: Optional pre-configured WebDriver instance (for browser pooling)
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.enable_ai = enable_ai
        self.driver = driver  # Use provided driver or create new one

        # Original modules
        self.login_module = None
        self.posting_module = None
        self.reply_module = None
        self.engagement_module = None
        self.messaging_module = None

        # AI-powered modules
        self.ai_service = None
        self.content_generator = None
        self.relevance_scorer = None
        self.profile_analyzer = None
        self.safety_manager = None
        self.analytics = None

        # Job search module
        self.job_search_module = None

    def setup_driver(self):
        """Setup Selenium WebDriver (unless one was provided)"""
        # Skip setup if driver was already provided (browser pooling)
        if self.driver is not None:
            utils.log("Using provided WebDriver from browser pool", "SUCCESS")
            return

        utils.log("Setting up WebDriver...")

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent
        user_agent = utils.get_random_user_agent()
        chrome_options.add_argument(f'user-agent={user_agent}')

        # Other options
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")          # Required on headless Linux servers
        chrome_options.add_argument("--window-size=1920,1080")  # Ensure proper rendering headless

        # Initialize driver (Selenium 4.6+ auto-manages ChromeDriver)
        self.driver = webdriver.Chrome(options=chrome_options)

        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        utils.log("WebDriver setup complete", "SUCCESS")

    def initialize_modules(self):
        """Initialize all bot modules"""
        utils.log("Initializing modules...")

        # Initialize AI services first
        if self.enable_ai:
            try:
                self.ai_service = AIService()
                self.content_generator = ContentGenerator(self.ai_service)
                self.relevance_scorer = RelevanceScorer(self.ai_service)
                self.profile_analyzer = ProfileAnalyzer(self.driver, self.ai_service)
                utils.log("AI modules initialized", "SUCCESS")
            except Exception as e:
                utils.log(f"AI initialization failed: {str(e)}. Falling back to non-AI mode.", "WARNING")
                self.enable_ai = False

        # Initialize safety and analytics (always enabled)
        self.safety_manager = SafetyManager()
        self.analytics = Analytics()

        # Initialize original modules with AI enhancements
        self.login_module = LinkedInLogin(self.driver, self.email, self.password)
        self.posting_module = LinkedInPosting(self.driver, content_generator=self.content_generator)
        self.reply_module = LinkedInAutoReply(self.driver)
        self.engagement_module = LinkedInEngagement(
            self.driver,
            ai_service=self.ai_service,
            relevance_scorer=self.relevance_scorer
        )
        self.messaging_module = LinkedInMessaging(self.driver)
        self.job_search_module = LinkedInJobSearch(self.driver)

        utils.log("All modules initialized", "SUCCESS")

    def start(self):
        """Start the bot"""
        utils.log("Starting LinkedIn Bot...", "SUCCESS")

        # Setup driver
        self.setup_driver()

        # Initialize modules
        self.initialize_modules()

        # Login
        if self.login_module.login():
            utils.log("Bot is ready!", "SUCCESS")
            return True
        else:
            utils.log("Failed to login", "ERROR")
            return False

    def is_session_alive(self):
        """Check if browser session is still active"""
        try:
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    def recover_session(self):
        """Recover from a dead browser session by restarting and re-logging in"""
        utils.log("Session lost. Recovering...", "WARNING")
        try:
            self.driver.quit()
        except Exception:
            pass

        self.setup_driver()

        # Update driver reference in all modules
        self.login_module.driver = self.driver
        self.posting_module.driver = self.driver
        self.reply_module.driver = self.driver
        self.engagement_module.driver = self.driver
        self.messaging_module.driver = self.driver
        if self.job_search_module:
            self.job_search_module.driver = self.driver
        if self.profile_analyzer:
            self.profile_analyzer.driver = self.driver

        if self.login_module.login():
            utils.log("Session recovered successfully!", "SUCCESS")
            return True
        else:
            utils.log("Session recovery failed", "ERROR")
            return False

    def ensure_session(self):
        """Ensure browser session is alive, recover if not"""
        if not self.is_session_alive():
            return self.recover_session()
        return True

    def stop(self):
        """Stop the bot and close browser"""
        utils.log("Stopping bot...")

        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

        utils.log("Bot stopped", "SUCCESS")

    # Posting methods
    def create_post(self, content, media_path=None):
        """Create a single post"""
        self.ensure_session()
        return self.posting_module.create_post(content, media_path)

    def check_scheduled_posts(self, posts_file):
        """Check and post scheduled posts"""
        self.ensure_session()
        return self.posting_module.check_and_post_scheduled(posts_file)

    # Engagement methods
    def engage_with_feed(self, max_engagements=10):
        """Engage with feed posts"""
        self.ensure_session()
        return self.engagement_module.engage_with_feed(max_engagements)

    def search_and_engage(self, keyword, max_engagements=5):
        """Search for keyword and engage"""
        self.ensure_session()
        return self.engagement_module.search_and_engage(keyword, max_engagements)

    def load_engagement_config(self, config_file):
        """Load engagement configuration"""
        self.engagement_module.load_engagement_config(config_file)

    def reply_based_engagement(self, max_replies=10):
        """
        Engage ONLY by replying to people who commented on your posts/comments
        Conservative, relationship-building approach
        """
        self.ensure_session()
        return self.engagement_module.reply_based_engagement(max_replies)

    # Reply methods
    def reply_to_comments(self, max_replies=5):
        """Reply to comments on your posts"""
        self.ensure_session()
        return self.reply_module.reply_to_comments(max_replies)

    def load_reply_templates(self, templates_file):
        """Load reply templates"""
        self.reply_module.load_reply_templates(templates_file)

    # Messaging methods
    def send_message(self, recipient_url, message_text):
        """Send a message"""
        self.ensure_session()
        return self.messaging_module.send_message(recipient_url, message_text)

    def send_connection_request(self, recipient_url, message_text):
        """Send connection request with message"""
        return self.messaging_module.send_connection_request_with_message(
            recipient_url, message_text
        )

    def check_messages(self, auto_respond=True, response_template=None):
        """Check and optionally respond to messages"""
        return self.messaging_module.check_and_respond_to_messages(
            auto_respond, response_template
        )

    def send_bulk_messages(self, recipients_file, message_template):
        """Send bulk messages"""
        return self.messaging_module.send_bulk_messages(recipients_file, message_template)

    # AI-Powered Methods
    def generate_and_post_content(self, theme=None):
        """Generate and post AI-created content"""
        if not self.content_generator:
            utils.log("Content generator not available", "ERROR")
            return False

        result = self.posting_module.create_ai_generated_post(theme=theme)
        if result and self.analytics:
            # Log to analytics
            self.analytics.log_post("AI-generated content", theme or "auto", is_ai_generated=True)
        return result

    def intelligent_feed_engagement(self, max_posts=10):
        """Engage with feed using AI filtering"""
        if not self.safety_manager:
            return self.engage_with_feed(max_posts)

        # Check safety limits
        allowed, reason = self.safety_manager.check_action_allowed('likes')
        if not allowed:
            utils.log(f"Engagement blocked: {reason}", "WARNING")
            return 0

        # Engage with AI filtering
        count = self.engagement_module.engage_with_feed(max_posts, use_ai=self.enable_ai)

        # Log actions to safety manager
        if self.safety_manager:
            for _ in range(count):
                self.safety_manager.log_action('likes')

        return count

    def schedule_video_content(self, days=7, video_folder=None):
        """
        Pre-generate AI content paired with videos and schedule for future posting

        Args:
            days: Number of days to schedule
            video_folder: Folder containing video files to attach
        """
        if not self.content_generator:
            utils.log("Content generator not available", "ERROR")
            return []

        return self.content_generator.schedule_content(
            days=days,
            video_folder=video_folder
        )

    def preview_scheduled_content(self):
        """Preview all pending scheduled AI content"""
        if not self.content_generator:
            utils.log("Content generator not available", "ERROR")
            return []

        return self.content_generator.preview_scheduled()

    def check_ai_scheduled_posts(self):
        """Check and post any AI-scheduled content that is due"""
        self.ensure_session()
        count = self.posting_module.check_and_post_ai_scheduled()
        if count > 0 and self.analytics:
            for _ in range(count):
                self.analytics.log_post("Scheduled AI content", "scheduled", is_ai_generated=True)
        return count

    def view_analytics(self):
        """Display analytics dashboard"""
        if self.analytics:
            self.analytics.print_dashboard()
        else:
            utils.log("Analytics not available", "ERROR")

    def get_ai_usage_stats(self):
        """Get AI API usage statistics"""
        if self.ai_service:
            return self.ai_service.get_api_usage_stats()
        return None

    # Full Autopilot
    def run_full_autopilot(self, max_posts_to_engage=10, max_connections=5):
        """
        Full autopilot: post content, engage with feed, and send connection requests

        Args:
            max_posts_to_engage: Max posts to engage with in feed
            max_connections: Max connection requests to send

        Returns:
            dict: Summary of actions taken
        """
        results = {
            'content_posted': False,
            'posts_engaged': 0,
            'connections_sent': 0,
        }

        self.ensure_session()

        # Step 1: Generate and post AI content
        print("\n[1/3] Generating and posting AI content...")
        utils.log("Autopilot Step 1: AI Content Generation")

        # Try posting scheduled content first, if none due, generate fresh
        scheduled_count = self.check_ai_scheduled_posts()
        if scheduled_count > 0:
            results['content_posted'] = True
            utils.log(f"Posted {scheduled_count} scheduled post(s)")
        else:
            if self.generate_and_post_content():
                results['content_posted'] = True
                utils.log("Posted fresh AI-generated content")
            else:
                utils.log("No content posted this round", "WARNING")

        utils.random_delay(5, 10)

        # Step 2: Intelligent feed engagement (like + comment)
        print("\n[2/3] Engaging with feed (like + comment)...")
        utils.log("Autopilot Step 2: Feed Engagement")

        count = self.intelligent_feed_engagement(max_posts=max_posts_to_engage)
        results['posts_engaged'] = count

        utils.random_delay(5, 10)

        # Step 3: Network outreach — find and connect with relevant people
        print("\n[3/3] Networking outreach...")
        utils.log("Autopilot Step 3: Connection Outreach")

        connections = self._autopilot_network_outreach(max_connections=max_connections)
        results['connections_sent'] = connections

        # Print summary
        print("\n" + "=" * 60)
        print("Autopilot Complete")
        print("=" * 60)
        print(f"  Content posted:    {'Yes' if results['content_posted'] else 'No'}")
        print(f"  Posts engaged:     {results['posts_engaged']}")
        print(f"  Connections sent:  {results['connections_sent']}")
        print("=" * 60)

        return results

    def _autopilot_network_outreach(self, max_connections=5):
        """
        Search for relevant people and send personalized connection requests

        Args:
            max_connections: Maximum connection requests to send

        Returns:
            int: Number of connection requests sent
        """
        # Check safety limits
        if self.safety_manager:
            allowed, reason = self.safety_manager.check_action_allowed('connection_requests')
            if not allowed:
                utils.log(f"Connection requests blocked: {reason}", "WARNING")
                return 0

            remaining = self.safety_manager.get_remaining_actions('connection_requests')
            max_connections = min(max_connections, remaining)

            if max_connections <= 0:
                utils.log("No more connection requests allowed today", "WARNING")
                return 0

        # Load job seeking config for search keywords
        try:
            with open('data/job_seeking_config.json', 'r') as f:
                job_config = json.load(f)
        except Exception:
            job_config = {'keywords_to_track': ['hiring software engineer']}

        # Load user profile for message personalization
        try:
            with open('data/content_strategy.json', 'r') as f:
                content_config = json.load(f)
                user_profile = content_config.get('user_profile', {})
        except Exception:
            user_profile = {'industry': 'software development', 'skills': ['Python']}

        connections_sent = 0
        keywords = job_config.get('keywords_to_track', ['hiring', 'software engineer'])

        # Pick a random keyword to search for people
        search_keyword = random.choice(keywords)
        utils.log(f"Searching for people related to: {search_keyword}")

        try:
            from selenium.webdriver.common.by import By

            # Search for people on LinkedIn
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_keyword}&origin=GLOBAL_SEARCH_HEADER"
            self.driver.get(search_url)
            utils.random_delay(3, 5)

            # Find profile cards in search results
            profile_cards = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'reusable-search__result-container')]"
            )

            if not profile_cards:
                profile_cards = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'entity-result__item')]"
                )

            utils.log(f"Found {len(profile_cards)} people in search results")

            for card in profile_cards:
                if connections_sent >= max_connections:
                    break

                try:
                    # Extract profile info from search card
                    name = ""
                    title = ""
                    profile_url = ""

                    try:
                        name_el = card.find_element(
                            By.XPATH,
                            ".//span[contains(@class, 'entity-result__title-text')]//a//span/span"
                        )
                        name = name_el.text.strip()
                    except Exception:
                        try:
                            name_el = card.find_element(By.XPATH, ".//span[@dir='ltr']")
                            name = name_el.text.strip()
                        except Exception:
                            pass

                    try:
                        title_el = card.find_element(
                            By.XPATH,
                            ".//div[contains(@class, 'entity-result__primary-subtitle')]"
                        )
                        title = title_el.text.strip()
                    except Exception:
                        pass

                    try:
                        link_el = card.find_element(By.XPATH, ".//a[contains(@href, '/in/')]")
                        profile_url = link_el.get_attribute('href')
                    except Exception:
                        continue  # Skip if no profile link

                    if not profile_url or not name:
                        continue

                    # Analyze profile value using AI
                    profile_data = {'name': name, 'title': title, 'company': '', 'bio': '', 'context': ''}

                    if self.ai_service:
                        analysis = self.ai_service.analyze_profile(profile_data)
                    else:
                        analysis = {'is_relevant': True, 'connection_value': 0.5}

                    if not analysis.get('is_relevant', False) and analysis.get('connection_value', 0) < 0.4:
                        utils.log(f"Skipping {name} — not relevant enough")
                        continue

                    # Generate personalized connection message
                    recipient_profile = {
                        'name': name,
                        'title': title,
                        'company': '',
                        'context': f'Found via search for: {search_keyword}'
                    }

                    if self.ai_service:
                        message = self.ai_service.generate_personalized_message(
                            recipient_profile=recipient_profile,
                            sender_profile=user_profile,
                            purpose='networking'
                        )
                    else:
                        industry = user_profile.get('industry', 'tech')
                        if isinstance(industry, list):
                            industry = industry[0]
                        message = f"Hi {name}, I came across your profile and would love to connect! I'm in {industry} and always looking to grow my network."

                    # Send connection request
                    utils.log(f"Sending connection request to {name} ({title})")

                    if self.messaging_module.send_connection_request_with_message(profile_url, message):
                        connections_sent += 1

                        if self.safety_manager:
                            self.safety_manager.log_action('connection_requests')

                        if self.analytics:
                            self.analytics.log_connection(
                                profile_url=profile_url,
                                name=name,
                                title=title,
                                is_recruiter=analysis.get('is_recruiter', False),
                                is_hiring_manager=analysis.get('is_hiring_manager', False),
                                connection_value=analysis.get('connection_value', 0.0)
                            )

                        utils.log(f"Connection request sent to {name}", "SUCCESS")

                        # Delay between connection requests
                        if self.safety_manager:
                            min_delay, max_delay = self.safety_manager.get_recommended_delay('connection_requests')
                            utils.random_delay(min_delay, max_delay)
                        else:
                            utils.random_delay(30, 60)
                    else:
                        utils.log(f"Failed to send connection request to {name}", "WARNING")
                        utils.random_delay(5, 10)

                except Exception as e:
                    utils.log(f"Error processing profile: {str(e)}", "ERROR")
                    continue

        except Exception as e:
            utils.log(f"Error in network outreach: {str(e)}", "ERROR")

        utils.log(f"Network outreach complete: {connections_sent} connection requests sent", "SUCCESS")
        return connections_sent

    # Utility methods
    def take_screenshot(self, filename="screenshot.png"):
        """Take a screenshot"""
        try:
            utils.ensure_directory("screenshots")
            filepath = os.path.join("screenshots", filename)
            self.driver.save_screenshot(filepath)
            utils.log(f"Screenshot saved: {filepath}")
        except Exception as e:
            utils.log(f"Error taking screenshot: {str(e)}", "ERROR")

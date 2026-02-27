"""
LinkedIn Engagement Module (AI-Powered Version)
Intelligently engages with relevant posts using AI filtering and contextual comments
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import utils
import json
import random
import hashlib

class LinkedInEngagement:
    def __init__(self, driver, ai_service=None, relevance_scorer=None):
        """
        Initialize LinkedIn Engagement Module

        Args:
            driver: Selenium WebDriver instance
            ai_service: AIService instance for AI-powered features
            relevance_scorer: RelevanceScorer instance for filtering posts
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.ai_service = ai_service
        self.relevance_scorer = relevance_scorer
        self.engagement_config = {}
        self.user_profile = None

        # Load user profile for context
        try:
            with open('data/content_strategy.json', 'r', encoding='utf-8') as f:
                strategy = json.load(f)
                self.user_profile = strategy.get('user_profile', {})
        except:
            self.user_profile = {
                'industry': 'software development',
                'skills': ['Python'],
                'interests': ['technology']
            }

    def load_engagement_config(self, config_file):
        """Load engagement configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.engagement_config = json.load(f)
            utils.log(f"Loaded engagement config from {config_file}")
        except Exception as e:
            utils.log(f"Error loading config: {str(e)}", "ERROR")

    def engage_with_feed(self, max_engagements=10, use_ai=True, progress_callback=None):
        """
        Intelligently engage with posts in feed

        Args:
            max_engagements: Maximum number of posts to engage with
            use_ai: Whether to use AI filtering (True) or legacy random method (False)
            progress_callback: Optional function to call with progress updates
                               Signature: callback(message: str, screenshot_path: str = None)

        Returns:
            int: Number of posts engaged with
        """
        try:
            utils.log("Starting intelligent feed engagement...")

            # Notify user we're starting
            if progress_callback:
                progress_callback("🔄 Loading LinkedIn feed...")

            # Navigate to feed
            self.driver.get("https://www.linkedin.com/feed/")
            utils.random_delay(2, 4)

            # Send screenshot of feed loaded
            if progress_callback:
                progress_callback("📸 Feed loaded, analyzing posts...", take_screenshot=True)

            engagement_count = 0
            like_count = 0
            comment_count = 0
            posts_analyzed = 0

            # Scroll and find posts
            posts = self._get_feed_posts()

            if not posts:
                utils.log("No posts found in feed", "WARNING")
                if progress_callback:
                    progress_callback("⚠️ No posts found in feed")
                return 0

            utils.log(f"Found {len(posts)} posts, analyzing for relevance...")

            # Notify user of post count
            if progress_callback:
                progress_callback(f"📊 Found {len(posts)} posts, filtering for relevance...")

            for post in posts:
                if engagement_count >= max_engagements:
                    break

                try:
                    posts_analyzed += 1

                    # Scroll to post
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", post)
                    utils.random_delay(1, 2)

                    # Extract post information
                    post_content = self._extract_post_content(post)
                    author_info = self._extract_author_info(post)
                    post_id = self._get_post_id(post)

                    if not post_content:
                        continue

                    # Use AI to determine if we should engage
                    if use_ai and self.relevance_scorer:
                        should_engage, relevance_score, reason = self.relevance_scorer.should_engage(
                            post_id=post_id,
                            post_content=post_content,
                            author_name=author_info.get('name', ''),
                            author_title=author_info.get('title', ''),
                            user_profile=self.user_profile
                        )

                        if not should_engage:
                            utils.log(f"Skipping post: {reason}")
                            continue

                        utils.log(f"Engaging with relevant post (score: {relevance_score:.2f})")
                    else:
                        # Legacy random engagement (fallback)
                        if random.random() > 0.5:
                            utils.log("Legacy mode: randomly skipping post")
                            continue

                    # Engage: like + comment on relevant posts
                    comment_prob = self.engagement_config.get('engagement_preferences', {}).get('comment_probability', 1.0)

                    action_taken = False

                    # Always like relevant posts
                    if self._like_post(post):
                        like_count += 1
                        action_taken = True

                        # Send update after every 2 likes
                        if like_count % 2 == 0 and progress_callback:
                            progress_callback(
                                f"👍 Progress: {like_count} likes, {comment_count} comments\n"
                                f"📊 Analyzed {posts_analyzed} posts",
                                take_screenshot=(like_count % 4 == 0)  # Screenshot every 4 likes
                            )

                        utils.random_delay(1, 3)

                    # Comment based on probability (comments are high-value engagement)
                    if random.random() < comment_prob:
                        if self._intelligent_comment_on_post(post, post_content, author_info, post_id):
                            comment_count += 1
                            action_taken = True

                            # Send update after every comment (higher value action)
                            if progress_callback:
                                author_name = author_info.get('name', 'Unknown')[:30]
                                progress_callback(
                                    f"💬 Commented on post by {author_name}\n"
                                    f"📊 Total: {like_count} likes, {comment_count} comments",
                                    take_screenshot=True  # Screenshot every comment
                                )

                            utils.random_delay(3, 6)

                    if action_taken:
                        engagement_count += 1

                    # Add delay between posts (human-like behavior)
                    utils.random_delay(2, 5)

                except Exception as e:
                    utils.log(f"Error engaging with post: {str(e)}", "ERROR")
                    continue

            # Send final summary
            if progress_callback:
                progress_callback(
                    f"✅ Engagement Complete!\n\n"
                    f"📊 Results:\n"
                    f"  • Analyzed: {posts_analyzed} posts\n"
                    f"  • Liked: {like_count} posts\n"
                    f"  • Commented: {comment_count} times\n\n"
                    f"Great work building your LinkedIn presence! 🎉",
                    take_screenshot=True
                )

            utils.log(f"Engagement complete: Analyzed {posts_analyzed} posts, {like_count} likes, {comment_count} comments", "SUCCESS")
            return engagement_count

        except Exception as e:
            utils.log(f"Error in engage_with_feed: {str(e)}", "ERROR")
            if progress_callback:
                progress_callback(f"❌ Error during engagement: {str(e)}")
            return 0

    def _get_feed_posts(self):
        """Get posts from feed"""
        try:
            # Scroll a bit to load posts
            utils.scroll_slowly(self.driver, scroll_pause_time=1)

            posts = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'feed-shared-update-v2')]"
            )

            utils.log(f"Found {len(posts)} posts in feed")
            return posts

        except Exception as e:
            utils.log(f"Error getting feed posts: {str(e)}", "ERROR")
            return []

    def _extract_post_content(self, post_element):
        """
        Extract text content from a post

        Args:
            post_element: Selenium WebElement for the post

        Returns:
            str: Post content text
        """
        try:
            # Try multiple selectors for post content
            selectors = [
                ".//div[contains(@class, 'feed-shared-update-v2__description')]",
                ".//span[contains(@dir, 'ltr')]",
                ".//div[contains(@class, 'feed-shared-text')]"
            ]

            for selector in selectors:
                try:
                    content_element = post_element.find_element(By.XPATH, selector)
                    content = content_element.text.strip()
                    if content:
                        return content
                except NoSuchElementException:
                    continue

            return ""

        except Exception as e:
            utils.log(f"Error extracting post content: {str(e)}", "ERROR")
            return ""

    def _extract_author_info(self, post_element):
        """
        Extract author information from a post

        Args:
            post_element: Selenium WebElement for the post

        Returns:
            dict: Author info with name and title
        """
        author_info = {'name': '', 'title': ''}

        try:
            # Try to find author name
            try:
                name_element = post_element.find_element(
                    By.XPATH,
                    ".//span[contains(@class, 'feed-shared-actor__name')]"
                )
                author_info['name'] = name_element.text.strip()
            except NoSuchElementException:
                pass

            # Try to find author title
            try:
                title_element = post_element.find_element(
                    By.XPATH,
                    ".//span[contains(@class, 'feed-shared-actor__description')]"
                )
                author_info['title'] = title_element.text.strip()
            except NoSuchElementException:
                pass

        except Exception as e:
            utils.log(f"Error extracting author info: {str(e)}", "ERROR")

        return author_info

    def _get_post_id(self, post_element):
        """
        Generate a stable unique identifier for a post

        Args:
            post_element: Selenium WebElement for the post

        Returns:
            str: Unique post identifier (stable across restarts)
        """
        try:
            # Try to get data-urn or other unique attribute
            post_id = post_element.get_attribute('data-urn')
            if post_id:
                return post_id

            # Fallback: stable hash from content + author
            content = self._extract_post_content(post_element)
            author = self._extract_author_info(post_element)
            raw = f"{author.get('name', '')}:{content[:150]}"
            return hashlib.md5(raw.encode()).hexdigest()
        except:
            # Last resort: hash whatever text is in the element
            try:
                text = post_element.text[:200]
                return hashlib.md5(text.encode()).hexdigest()
            except:
                return "unknown_" + str(random.randint(1000000, 9999999))

    def _like_post(self, post_element):
        """Like a post"""
        try:
            # Find like button within post
            like_button = post_element.find_element(
                By.XPATH,
                ".//button[contains(@aria-label, 'React Like') or contains(@aria-label, 'Like')]"
            )

            # Check if already liked
            if 'true' in like_button.get_attribute('aria-pressed'):
                utils.log("Post already liked, skipping")
                return False

            like_button.click()
            utils.log("Liked post")
            return True

        except NoSuchElementException:
            utils.log("Like button not found", "WARNING")
            return False
        except Exception as e:
            utils.log(f"Error liking post: {str(e)}", "ERROR")
            return False

    def _intelligent_comment_on_post(self, post_element, post_content, author_info, post_id):
        """
        Comment on a post using AI-generated contextual comment

        Args:
            post_element: Selenium WebElement for the post
            post_content: The text content of the post
            author_info: Dict with author name and title
            post_id: Unique post identifier

        Returns:
            bool: True if comment was successful
        """
        try:
            # CRITICAL: Triple-check we haven't already commented on this post
            if self.relevance_scorer and self.relevance_scorer.has_commented_on_post(post_id):
                utils.log(f"Already commented on post {post_id[:16]}... — skipping to prevent duplicate", "WARNING")
                return False

            # Additional check: verify we're not already in comment mode for this post
            try:
                # Check if we already have an open comment box (indicator of previous comment attempt)
                existing_comment = post_element.find_element(
                    By.XPATH,
                    ".//div[contains(@class, 'comments-comment-item__main-content')]//span[contains(@class, 'hoverable-link-text')]"
                )
                if existing_comment and existing_comment.text:
                    # Check if it's our own comment by looking for "You" or our name
                    if "You" in existing_comment.text or existing_comment.get_attribute('aria-label') == "View profile for You":
                        utils.log(f"We already commented on this post (found our comment) — skipping", "WARNING")
                        # Mark it as commented even if we didn't have it tracked
                        if self.relevance_scorer:
                            self.relevance_scorer.mark_post_commented(post_id)
                        return False
            except NoSuchElementException:
                # No existing comment found, safe to proceed
                pass

            # Step 1: Click the comment button to open comment box
            utils.log("Attempting to comment on post...")
            comment_button = None

            comment_button_selectors = [
                ".//button[contains(@aria-label, 'Comment')]",
                ".//button[contains(@aria-label, 'comment')]",
                ".//span[text()='Comment']/ancestor::button",
                ".//button[contains(@class, 'comment')]",
                ".//button[.//li-icon[@type='comment']]",
                ".//button[.//svg[contains(@class, 'comment')]]",
            ]

            for selector in comment_button_selectors:
                try:
                    comment_button = post_element.find_element(By.XPATH, selector)
                    if comment_button:
                        break
                except NoSuchElementException:
                    continue

            if not comment_button:
                utils.log("Comment button not found on this post", "WARNING")
                return False

            comment_button.click()
            utils.log("Clicked comment button")
            utils.random_delay(2, 3)

            # Step 2: Find the comment text box — search ONLY within the post element
            # (no page-wide fallback: that causes comments on wrong/already-commented posts)
            comment_box = None

            comment_box_selectors = [
                ".//div[@role='textbox' and contains(@aria-label, 'comment')]",
                ".//div[@role='textbox' and contains(@aria-label, 'Comment')]",
                ".//div[@role='textbox' and contains(@aria-placeholder, 'comment')]",
                ".//div[contains(@class, 'ql-editor') and @role='textbox']",
                ".//div[@contenteditable='true' and contains(@class, 'comment')]",
                ".//div[@role='textbox']",
            ]

            for selector in comment_box_selectors:
                try:
                    comment_box = post_element.find_element(By.XPATH, selector)
                    if comment_box:
                        break
                except NoSuchElementException:
                    continue

            if not comment_box:
                utils.log("Comment text box not found within post — skipping to avoid commenting on wrong post", "WARNING")
                return False

            # Step 3: Click and focus the comment box
            comment_box.click()
            utils.random_delay(0.5, 1)

            # Step 4: Generate AI comment
            comment_text = self._generate_contextual_comment(
                post_content,
                author_info.get('name', ''),
                author_info.get('title', '')
            )
            utils.log(f"Generated comment: {comment_text[:60]}...")

            # Step 5: Type the comment
            utils.human_type(comment_box, comment_text)
            utils.random_delay(1, 2)

            # Step 6: Submit the comment
            # Try multiple submit methods
            submitted = False

            # Method 1: Click the post/submit button
            submit_selectors = [
                ".//button[contains(@class, 'comments-comment-box__submit-button')]",
                "//button[contains(@class, 'comments-comment-box__submit-button')]",
                ".//button[contains(@aria-label, 'Post comment')]",
                "//button[contains(@aria-label, 'Post comment')]",
                ".//button[text()='Post']",
                "//button[text()='Post']",
            ]
            for selector in submit_selectors:
                try:
                    search_context = post_element if selector.startswith('.') else self.driver
                    submit_btn = search_context.find_element(By.XPATH, selector)
                    if submit_btn and submit_btn.is_enabled():
                        submit_btn.click()
                        submitted = True
                        break
                except:
                    continue

            # Method 2: Keyboard shortcut fallback
            if not submitted:
                comment_box.send_keys(Keys.CONTROL, Keys.RETURN)
                submitted = True

            utils.random_delay(1, 2)

            # Close the comment thread so it doesn't stay open for subsequent posts
            try:
                comment_box.send_keys(Keys.ESCAPE)
            except Exception:
                pass

            # Mark this post as commented to prevent duplicates
            if self.relevance_scorer:
                self.relevance_scorer.mark_post_commented(post_id)

            utils.log(f"Posted comment: {comment_text[:50]}...", "SUCCESS")
            return True

        except NoSuchElementException:
            utils.log("Comment elements not found on this post", "WARNING")
            return False
        except Exception as e:
            utils.log(f"Error commenting: {str(e)}", "ERROR")
            return False

    def _generate_contextual_comment(self, post_content, author_name="", author_title=""):
        """
        Generate a contextual comment using AI

        Args:
            post_content: The post content to comment on
            author_name: Name of the post author
            author_title: Title of the author

        Returns:
            str: Generated comment
        """
        if self.ai_service:
            try:
                comment = self.ai_service.generate_contextual_comment(
                    post_content=post_content,
                    author_name=author_name,
                    author_title=author_title,
                    user_profile=self.user_profile
                )
                return comment
            except Exception as e:
                utils.log(f"AI comment generation failed: {str(e)}", "WARNING")
                return self._get_random_comment()
        else:
            return self._get_random_comment()

    def _get_random_comment(self):
        """Get random generic comment (legacy fallback)"""
        comments = self.engagement_config.get('engagement_preferences', {}).get('generic_comments', [
            "Great post!",
            "Thanks for sharing!",
            "Very insightful!"
        ])
        return random.choice(comments)

    def reply_based_engagement(self, max_replies=10):
        """
        Engage ONLY by replying to people who commented on your posts/comments
        This is a conservative, relationship-building approach

        Args:
            max_replies: Maximum number of replies to post

        Returns:
            int: Number of replies posted
        """
        try:
            utils.log("Starting reply-based engagement (only responding to people who engaged with you)...")

            # Navigate to notifications
            self.driver.get("https://www.linkedin.com/notifications/")
            utils.random_delay(2, 4)

            reply_count = 0
            replied_notifications = set()

            # Get notifications
            notifications = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'notification-card')]"
            )

            utils.log(f"Found {len(notifications)} notifications")

            for notification in notifications:
                if reply_count >= max_replies:
                    break

                try:
                    notification_text = notification.text.lower()
                    notification_id = notification.get_attribute('data-id') or notification.text[:50]

                    # Skip if already processed
                    if notification_id in replied_notifications:
                        continue

                    # Only process comments on YOUR posts or replies to YOUR comments
                    is_relevant = (
                        'commented on your' in notification_text or
                        'replied to your comment' in notification_text or
                        ('commented' in notification_text and 'your' in notification_text)
                    )

                    if not is_relevant:
                        continue

                    utils.log(f"Replying to: {notification_text[:80]}...")

                    # Click notification to go to the post
                    notification.click()
                    utils.random_delay(2, 3)

                    # Try to reply to the comment
                    if self._reply_to_comment_on_page():
                        reply_count += 1
                        replied_notifications.add(notification_id)
                        utils.log(f"Posted reply ({reply_count}/{max_replies})", "SUCCESS")
                        utils.random_delay(3, 5)

                    # Return to notifications
                    self.driver.get("https://www.linkedin.com/notifications/")
                    utils.random_delay(2, 3)

                    # Re-find notifications after page reload
                    notifications = self.driver.find_elements(
                        By.XPATH,
                        "//li[contains(@class, 'notification-card')]"
                    )

                except Exception as e:
                    utils.log(f"Error processing notification: {str(e)}", "ERROR")
                    continue

            utils.log(f"Reply-based engagement complete: {reply_count} replies posted", "SUCCESS")
            return reply_count

        except Exception as e:
            utils.log(f"Error in reply_based_engagement: {str(e)}", "ERROR")
            return 0

    def _reply_to_comment_on_page(self):
        """Reply to a comment on the current page"""
        try:
            # Find the comment box (usually at the bottom of the comment thread)
            comment_box_selectors = [
                "//div[@role='textbox' and contains(@aria-label, 'comment')]",
                "//div[@role='textbox' and contains(@aria-placeholder, 'Add a comment')]",
                "//div[contains(@class, 'ql-editor') and @contenteditable='true']"
            ]

            comment_box = None
            for selector in comment_box_selectors:
                try:
                    comment_box = self.driver.find_element(By.XPATH, selector)
                    if comment_box:
                        break
                except NoSuchElementException:
                    continue

            if not comment_box:
                utils.log("Could not find comment box to reply", "WARNING")
                return False

            # Click to focus
            comment_box.click()
            utils.random_delay(0.5, 1)

            # Generate reply using AI (context-aware)
            reply_text = self._generate_reply_to_engagement()

            # Type the reply
            utils.human_type(comment_box, reply_text)
            utils.random_delay(1, 2)

            # Submit the reply
            submit_selectors = [
                "//button[contains(@class, 'comments-comment-box__submit-button')]",
                "//button[contains(text(), 'Post')]",
                "//button[@type='submit' and contains(@class, 'comment')]"
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.XPATH, selector)
                    if submit_btn and submit_btn.is_enabled():
                        submit_btn.click()
                        utils.log(f"Posted reply: {reply_text[:50]}...")
                        return True
                except:
                    continue

            # Fallback: keyboard shortcut
            from selenium.webdriver.common.keys import Keys
            comment_box.send_keys(Keys.CONTROL, Keys.RETURN)
            utils.log(f"Posted reply via keyboard: {reply_text[:50]}...")
            return True

        except Exception as e:
            utils.log(f"Error replying to comment: {str(e)}", "ERROR")
            return False

    def _generate_reply_to_engagement(self):
        """Generate a thoughtful reply to someone who engaged with your content"""
        if self.ai_service:
            try:
                # For now, use a simple appreciative reply
                # In the future, can enhance with AI to read the comment and generate contextual reply
                replies = [
                    "Thanks for your thoughtful comment! Really appreciate your perspective on this.",
                    "Great point! I hadn't considered that angle. Thanks for sharing!",
                    "Really glad this resonated with you! Would love to hear more about your experience with this.",
                    "Appreciate you taking the time to share your thoughts! This is exactly the kind of discussion I was hoping for.",
                    "Thank you! Your insight adds a lot to this conversation."
                ]
                import random
                return random.choice(replies)
            except:
                return "Thanks for your comment! I appreciate your input."
        else:
            return "Thanks for sharing your thoughts!"

    def search_and_engage(self, keyword, max_engagements=5, use_ai=True):
        """
        Search for posts with keyword and intelligently engage

        Args:
            keyword: Keyword to search for
            max_engagements: Maximum posts to engage with
            use_ai: Whether to use AI filtering

        Returns:
            int: Number of posts engaged with
        """
        try:
            utils.log(f"Searching for: {keyword}")

            # Navigate to search
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={keyword}"
            self.driver.get(search_url)
            utils.random_delay(3, 5)

            # Get posts from search results
            posts = self._get_feed_posts()

            engagement_count = 0

            for post in posts[:max_engagements * 2]:  # Analyze more posts, engage with fewer
                if engagement_count >= max_engagements:
                    break

                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", post)
                    utils.random_delay(1, 2)

                    # Extract post information
                    post_content = self._extract_post_content(post)
                    author_info = self._extract_author_info(post)
                    post_id = self._get_post_id(post)

                    # Use AI to determine relevance
                    if use_ai and self.relevance_scorer:
                        should_engage, relevance_score, reason = self.relevance_scorer.should_engage(
                            post_id=post_id,
                            post_content=post_content,
                            author_name=author_info.get('name', ''),
                            author_title=author_info.get('title', ''),
                            user_profile=self.user_profile
                        )

                        if not should_engage:
                            continue

                    # Engage with post: like + comment
                    liked = self._like_post(post)
                    if liked:
                        utils.random_delay(1, 3)

                    # Comment on search results too
                    comment_prob = self.engagement_config.get('engagement_preferences', {}).get('comment_probability', 0.6)
                    if random.random() < comment_prob:
                        post_content = post_content or self._extract_post_content(post)
                        if post_content:
                            self._intelligent_comment_on_post(post, post_content, author_info, post_id)
                            utils.random_delay(3, 6)

                    if liked:
                        engagement_count += 1

                except Exception as e:
                    utils.log(f"Error engaging with search result: {str(e)}", "ERROR")
                    continue

            utils.log(f"Engaged with {engagement_count} posts for keyword: {keyword}", "SUCCESS")
            return engagement_count

        except Exception as e:
            utils.log(f"Error in search_and_engage: {str(e)}", "ERROR")
            return 0

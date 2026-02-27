from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import utils
import json
import random

class LinkedInAutoReply:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.reply_templates = {}

    def load_reply_templates(self, templates_file):
        """Load reply templates from JSON file"""
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                self.reply_templates = json.load(f)
            utils.log(f"Loaded reply templates from {templates_file}")
        except Exception as e:
            utils.log(f"Error loading templates: {str(e)}", "ERROR")

    def check_notifications(self):
        """Check for new notifications"""
        try:
            utils.log("Checking notifications...")
            self.driver.get("https://www.linkedin.com/notifications/")
            utils.random_delay(2, 4)

            # Find notification items
            notifications = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'notification-card')]"
            )

            utils.log(f"Found {len(notifications)} notifications")
            return notifications

        except Exception as e:
            utils.log(f"Error checking notifications: {str(e)}", "ERROR")
            return []

    def reply_to_comments(self, max_replies=5):
        """Reply to comments on your posts and responses to your comments"""
        try:
            utils.log("Checking for comments to reply to...")

            # Go to notifications
            notifications = self.check_notifications()
            reply_count = 0
            replied_to_ids = set()  # Track which notifications we've replied to

            for notification in notifications:
                if reply_count >= max_replies:
                    break

                try:
                    # Check if it's a comment notification
                    text = notification.text.lower()
                    notification_id = notification.get_attribute('data-id') or notification.text[:50]

                    # Skip if we've already replied to this notification
                    if notification_id in replied_to_ids:
                        continue

                    # Only respond to comments ON your content or replies TO your comments
                    is_comment_on_my_post = 'commented on your' in text
                    is_reply_to_my_comment = 'replied to your comment' in text or 'replied' in text

                    if is_comment_on_my_post or is_reply_to_my_comment:
                        utils.log(f"Found relevant notification: {text[:80]}...")

                        # Click on notification
                        notification.click()
                        utils.random_delay(2, 3)

                        # Try to reply
                        if self._reply_to_current_comment():
                            reply_count += 1
                            replied_to_ids.add(notification_id)
                            utils.log(f"Replied successfully ({reply_count}/{max_replies})")
                            utils.random_delay(3, 5)

                        # Go back to notifications
                        self.driver.back()
                        utils.random_delay(2, 3)
                    else:
                        utils.log(f"Skipping notification (not a comment on my content): {text[:60]}...")

                except Exception as e:
                    utils.log(f"Error processing notification: {str(e)}", "ERROR")
                    continue

            utils.log(f"Replied to {reply_count} comments on your content", "SUCCESS")
            return reply_count

        except Exception as e:
            utils.log(f"Error in reply_to_comments: {str(e)}", "ERROR")
            return 0

    def _reply_to_current_comment(self):
        """Reply to comment on current page"""
        try:
            # Find comment section
            comment_box = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[@role='textbox' and contains(@aria-label, 'comment')]"
                ))
            )

            # Click on comment box
            comment_box.click()
            utils.random_delay(0.5, 1)

            # Select appropriate reply
            reply_text = self._select_reply_text()

            # Type reply
            utils.human_type(comment_box, reply_text)
            utils.random_delay(1, 2)

            # Click post comment button
            post_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'comment-submit-button') or contains(text(), 'Post')]"
            )
            post_button.click()

            utils.log(f"Replied: {reply_text}")
            return True

        except Exception as e:
            utils.log(f"Error replying to comment: {str(e)}", "ERROR")
            return False

    def _select_reply_text(self, comment_text=""):
        """Select appropriate reply text based on comment"""
        try:
            # Check for keywords in comment
            comment_lower = comment_text.lower()

            # Check keyword-based replies
            if self.reply_templates.get('keyword_based'):
                for keyword, reply in self.reply_templates['keyword_based'].items():
                    if keyword.lower() in comment_lower:
                        return reply

            # Check if it seems like a question
            if '?' in comment_text:
                if self.reply_templates.get('question_replies'):
                    return random.choice(self.reply_templates['question_replies'])

            # Use positive reply if certain positive keywords
            positive_keywords = ['great', 'awesome', 'amazing', 'excellent', 'love']
            if any(word in comment_lower for word in positive_keywords):
                if self.reply_templates.get('positive_replies'):
                    return random.choice(self.reply_templates['positive_replies'])

            # Default to generic reply
            if self.reply_templates.get('generic_replies'):
                return random.choice(self.reply_templates['generic_replies'])

            return "Thanks for your comment!"

        except Exception as e:
            utils.log(f"Error selecting reply: {str(e)}", "ERROR")
            return "Thanks for your comment!"

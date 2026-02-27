from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import utils
import json
from datetime import datetime

class LinkedInPosting:
    def __init__(self, driver, content_generator=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.content_generator = content_generator

    def create_ai_generated_post(self, theme=None, media_path=None):
        """
        Generate and post AI-created content

        Args:
            theme: Optional theme for the post
            media_path: Optional path to media file

        Returns:
            bool: True if post was successful
        """
        if not self.content_generator:
            utils.log("Content generator not available, cannot create AI post", "ERROR")
            return False

        try:
            utils.log("Generating AI post content...")

            # Generate content
            post_content = self.content_generator.generate_post(theme=theme)

            if not post_content:
                utils.log("Failed to generate post content", "ERROR")
                return False

            utils.log(f"Generated content: {post_content[:100]}...")

            # Create the post using the standard method
            result = self.create_post(post_content, media_path)

            if result:
                utils.log("AI-generated post published successfully!", "SUCCESS")

            return result

        except Exception as e:
            utils.log(f"Error creating AI-generated post: {str(e)}", "ERROR")
            return False

    def create_post(self, content, media_path=None):
        """Create a new LinkedIn post"""
        try:
            utils.log(f"Creating post: {content[:50]}...")

            # Navigate to feed if not already there
            self.driver.get("https://www.linkedin.com/feed/")
            utils.random_delay(2, 4)

            # Click on "Start a post" button
            start_post_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'artdeco-button') and contains(., 'Start a post')]"
                ))
            )
            start_post_button.click()
            utils.random_delay(1, 2)

            # Wait for the post editor to appear
            post_editor = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[@role='textbox' and @contenteditable='true']"
                ))
            )

            # Type the content (use JavaScript to handle all Unicode characters including emojis)
            utils.log("Typing post content...")
            post_editor.click()
            utils.random_delay(0.5, 1)
            utils.human_type(post_editor, content, typing_speed=0.05, use_javascript=True)
            utils.random_delay(1, 2)

            # Upload media if provided
            if media_path:
                utils.log("Uploading media...")
                self._upload_media(media_path)
                utils.random_delay(2, 3)

            # Click Post button
            utils.log("Publishing post...")
            post_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'share-actions__primary-action')]"
                ))
            )
            post_button.click()
            utils.random_delay(3, 5)

            utils.log("Post created successfully!", "SUCCESS")
            return True

        except TimeoutException:
            utils.log("Timeout while creating post", "ERROR")
            return False
        except Exception as e:
            utils.log(f"Error creating post: {str(e)}", "ERROR")
            return False

    def _upload_media(self, media_path):
        """Upload media (image or video) to post"""
        import os
        try:
            abs_path = os.path.abspath(media_path)
            ext = os.path.splitext(abs_path)[1].lower()
            is_video = ext in ['.mp4', '.mov', '.avi', '.wmv', '.mkv', '.webm']

            if is_video:
                self._upload_video(abs_path)
            else:
                self._upload_image(abs_path)

        except Exception as e:
            utils.log(f"Error uploading media: {str(e)}", "ERROR")

    def _upload_image(self, media_path):
        """Upload an image to post"""
        try:
            media_button = self.driver.find_element(
                By.XPATH,
                "//button[@aria-label='Add a photo']"
            )
            media_button.click()
            utils.random_delay(1, 2)

            file_input = self.driver.find_element(
                By.XPATH,
                "//input[@type='file']"
            )
            file_input.send_keys(media_path)
            utils.random_delay(2, 3)

        except Exception as e:
            utils.log(f"Error uploading image: {str(e)}", "ERROR")

    def _upload_video(self, video_path):
        """Upload a video to post"""
        try:
            # Click the video upload button
            video_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[@aria-label='Add a video']"
                ))
            )
            video_button.click()
            utils.random_delay(1, 2)

            # Find file input and send the video file
            file_input = self.driver.find_element(
                By.XPATH,
                "//input[@type='file']"
            )
            file_input.send_keys(video_path)
            utils.log(f"Uploading video: {video_path}...")

            # Wait for video to process (LinkedIn takes time to process videos)
            utils.random_delay(10, 20)

            # Check if video is still processing
            for _ in range(12):  # Wait up to ~2 more minutes
                try:
                    self.driver.find_element(
                        By.XPATH,
                        "//*[contains(text(), 'Processing') or contains(text(), 'Uploading')]"
                    )
                    utils.log("Video still processing, waiting...")
                    utils.random_delay(10, 15)
                except:
                    break  # No processing indicator found, video is ready

            utils.log("Video uploaded successfully", "SUCCESS")

        except Exception as e:
            utils.log(f"Error uploading video: {str(e)}", "ERROR")

    def load_scheduled_posts(self, posts_file):
        """Load scheduled posts from JSON file"""
        try:
            with open(posts_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            return posts
        except FileNotFoundError:
            utils.log(f"Posts file not found: {posts_file}", "ERROR")
            return []
        except json.JSONDecodeError:
            utils.log(f"Invalid JSON in posts file: {posts_file}", "ERROR")
            return []

    def save_scheduled_posts(self, posts, posts_file):
        """Save scheduled posts back to JSON file"""
        try:
            with open(posts_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            utils.log(f"Error saving posts: {str(e)}", "ERROR")

    def check_and_post_scheduled(self, posts_file):
        """Check for scheduled posts and post them if time matches"""
        posts = self.load_scheduled_posts(posts_file)
        current_time = datetime.now()
        posted_count = 0

        for post in posts:
            if post.get('posted', False):
                continue

            schedule_time = datetime.strptime(post['schedule_time'], '%Y-%m-%d %H:%M:%S')

            if current_time >= schedule_time:
                utils.log(f"Posting scheduled post ID: {post['id']}")

                if self.create_post(post['content'], post.get('media')):
                    post['posted'] = True
                    posted_count += 1
                    utils.random_delay(5, 10)  # Delay between posts

        if posted_count > 0:
            self.save_scheduled_posts(posts, posts_file)
            utils.log(f"Posted {posted_count} scheduled post(s)", "SUCCESS")

        return posted_count

    def check_and_post_ai_scheduled(self, schedule_file='data/scheduled_content.json'):
        """Check for scheduled AI-generated posts (with video support) and post if time matches"""
        posts = self.load_scheduled_posts(schedule_file)
        if not posts:
            return 0

        current_time = datetime.now()
        posted_count = 0

        for post in posts:
            if post.get('posted', False):
                continue

            schedule_time = datetime.strptime(post['schedule_time'], '%Y-%m-%d %H:%M:%S')

            if current_time >= schedule_time:
                media = post.get('media')
                media_type = post.get('media_type')
                utils.log(f"Posting scheduled AI content ID: {post['id']} | Theme: {post.get('theme', 'N/A')}" +
                          (f" | {media_type}" if media_type else ""))

                if self.create_post(post['content'], media):
                    post['posted'] = True
                    posted_count += 1
                    utils.random_delay(5, 10)

        if posted_count > 0:
            self.save_scheduled_posts(posts, schedule_file)
            utils.log(f"Posted {posted_count} scheduled AI content(s)", "SUCCESS")

        return posted_count

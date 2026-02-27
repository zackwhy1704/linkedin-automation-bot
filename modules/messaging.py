from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import utils
import json
import random

class LinkedInMessaging:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def send_message(self, recipient_url, message_text):
        """Send a message to a specific user"""
        try:
            utils.log(f"Sending message to: {recipient_url}")

            # Navigate to recipient profile
            self.driver.get(recipient_url)
            utils.random_delay(2, 4)

            # Click Message button
            message_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'message-anywhere-button') or contains(., 'Message')]"
                ))
            )
            message_button.click()
            utils.random_delay(1, 2)

            # Find message input box
            message_box = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[@role='textbox' and contains(@aria-label, 'message')]"
                ))
            )

            # Type message
            message_box.click()
            utils.random_delay(0.5, 1)
            utils.human_type(message_box, message_text)
            utils.random_delay(1, 2)

            # Send message
            send_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'msg-form__send-button') or contains(., 'Send')]"
            )
            send_button.click()

            utils.log("Message sent successfully!", "SUCCESS")
            utils.random_delay(2, 3)
            return True

        except TimeoutException:
            utils.log("Timeout while sending message", "ERROR")
            return False
        except Exception as e:
            utils.log(f"Error sending message: {str(e)}", "ERROR")
            return False

    def send_connection_request_with_message(self, recipient_url, message_text):
        """Send connection request with a message"""
        try:
            utils.log(f"Sending connection request to: {recipient_url}")

            # Navigate to recipient profile
            self.driver.get(recipient_url)
            utils.random_delay(2, 4)

            # Click Connect button
            connect_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@aria-label, 'Invite') or contains(., 'Connect')]"
                ))
            )
            connect_button.click()
            utils.random_delay(1, 2)

            # Click "Add a note" if available
            try:
                add_note_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(., 'Add a note')]"
                )
                add_note_button.click()
                utils.random_delay(1, 2)

                # Type message
                note_box = self.driver.find_element(
                    By.XPATH,
                    "//textarea[@name='message']"
                )
                note_box.click()
                utils.human_type(note_box, message_text)
                utils.random_delay(1, 2)

            except NoSuchElementException:
                utils.log("No 'Add a note' option available", "WARNING")

            # Click Send button
            send_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@aria-label, 'Send') or contains(., 'Send')]"
            )
            send_button.click()

            utils.log("Connection request sent!", "SUCCESS")
            utils.random_delay(2, 3)
            return True

        except Exception as e:
            utils.log(f"Error sending connection request: {str(e)}", "ERROR")
            return False

    def check_and_respond_to_messages(self, auto_respond=True, response_template=None):
        """Check for new messages and optionally auto-respond"""
        try:
            utils.log("Checking messages...")

            # Navigate to messaging
            self.driver.get("https://www.linkedin.com/messaging/")
            utils.random_delay(2, 4)

            # Find unread conversations
            unread_conversations = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'msg-conversation-card') and contains(@class, 'unread')]"
            )

            utils.log(f"Found {len(unread_conversations)} unread conversations")

            if not auto_respond or not response_template:
                return len(unread_conversations)

            # Respond to unread messages
            for conversation in unread_conversations[:5]:  # Limit to 5
                try:
                    conversation.click()
                    utils.random_delay(2, 3)

                    # Get message box
                    message_box = self.wait.until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//div[@role='textbox' and contains(@aria-label, 'message')]"
                        ))
                    )

                    # Type response
                    message_box.click()
                    utils.random_delay(0.5, 1)

                    response = self._get_auto_response(response_template)
                    utils.human_type(message_box, response)
                    utils.random_delay(1, 2)

                    # Send
                    message_box.send_keys(Keys.RETURN)
                    utils.log(f"Auto-responded: {response}")
                    utils.random_delay(3, 5)

                except Exception as e:
                    utils.log(f"Error responding to message: {str(e)}", "ERROR")
                    continue

            return len(unread_conversations)

        except Exception as e:
            utils.log(f"Error checking messages: {str(e)}", "ERROR")
            return 0

    def _get_auto_response(self, template):
        """Get auto response text"""
        if isinstance(template, list):
            return random.choice(template)
        return template or "Thanks for your message! I'll get back to you soon."

    def send_bulk_messages(self, recipients_file, message_template):
        """Send messages to multiple recipients from a file"""
        try:
            with open(recipients_file, 'r') as f:
                recipients = json.load(f)

            sent_count = 0

            for recipient in recipients:
                profile_url = recipient.get('profile_url')
                custom_message = recipient.get('message', message_template)

                if profile_url:
                    if self.send_message(profile_url, custom_message):
                        sent_count += 1
                        utils.random_delay(10, 15)  # Longer delay for bulk messages

            utils.log(f"Sent {sent_count} bulk messages", "SUCCESS")
            return sent_count

        except Exception as e:
            utils.log(f"Error in bulk messaging: {str(e)}", "ERROR")
            return 0

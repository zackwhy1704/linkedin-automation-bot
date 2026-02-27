from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import utils

class LinkedInLogin:
    def __init__(self, driver, email, password):
        self.driver = driver
        self.email = email
        self.password = password
        self.wait = WebDriverWait(driver, 10)

    def login(self):
        """Login to LinkedIn"""
        try:
            utils.log("Navigating to LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            utils.random_delay(2, 4)

            # Enter email
            utils.log("Entering email...")
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            utils.human_type(email_field, self.email)
            utils.random_delay(1, 2)

            # Enter password
            utils.log("Entering password...")
            password_field = self.driver.find_element(By.ID, "password")
            utils.human_type(password_field, self.password)
            utils.random_delay(1, 2)

            # Click login button
            utils.log("Clicking login button...")
            login_button = self.driver.find_element(
                By.XPATH, "//button[@type='submit']"
            )
            login_button.click()

            # Wait for navigation
            utils.random_delay(3, 5)

            # Check if login was successful
            if self._check_login_success():
                utils.log("Login successful!", "SUCCESS")
                return True
            else:
                utils.log("Login may have failed or requires verification", "WARNING")
                return False

        except TimeoutException:
            utils.log("Timeout during login", "ERROR")
            return False
        except Exception as e:
            utils.log(f"Error during login: {str(e)}", "ERROR")
            return False

    def _check_login_success(self):
        """Check if login was successful"""
        try:
            # Check for feed or home page elements
            self.wait.until(
                EC.presence_of_element_located((By.ID, "global-nav"))
            )
            return True
        except:
            return False

    def handle_verification(self):
        """Handle two-factor authentication or verification"""
        utils.log("Verification required. Please complete manually...", "WARNING")
        input("Press Enter after completing verification...")
        utils.random_delay(2, 3)

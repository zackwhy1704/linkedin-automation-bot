"""
Profile Analyzer Module
Analyzes LinkedIn profiles to identify recruiters, hiring managers, and valuable connections
"""

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import utils
import json

class ProfileAnalyzer:
    def __init__(self, driver, ai_service=None):
        """
        Initialize Profile Analyzer

        Args:
            driver: Selenium WebDriver instance
            ai_service: AIService for AI-powered analysis
        """
        self.driver = driver
        self.ai_service = ai_service
        self.job_seeking_config = self._load_job_seeking_config()

    def _load_job_seeking_config(self):
        """Load job seeking configuration"""
        try:
            with open('data/job_seeking_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'target_roles': ['Software Engineer']}

    def analyze_profile(self, profile_url):
        """
        Analyze a LinkedIn profile

        Args:
            profile_url: URL of the LinkedIn profile

        Returns:
            dict: Profile analysis with is_recruiter, is_hiring_manager, connection_value, etc.
        """
        try:
            utils.log(f"Analyzing profile: {profile_url}")

            # Navigate to profile
            self.driver.get(profile_url)
            utils.random_delay(2, 4)

            # Extract profile data
            profile_data = self._extract_profile_data()

            # Use AI to analyze if available
            if self.ai_service:
                analysis = self.ai_service.analyze_profile(
                    profile_data=profile_data,
                    user_job_search_config=self.job_seeking_config
                )
            else:
                analysis = self._simple_profile_analysis(profile_data)

            utils.log(f"Profile analysis complete: {analysis}", "SUCCESS")
            return analysis

        except Exception as e:
            utils.log(f"Error analyzing profile: {str(e)}", "ERROR")
            return {
                'is_recruiter': False,
                'is_hiring_manager': False,
                'is_relevant': False,
                'connection_value': 0.0
            }

    def _extract_profile_data(self):
        """
        Extract data from LinkedIn profile page

        Returns:
            dict: Profile data with name, title, company, bio, etc.
        """
        profile_data = {
            'name': '',
            'title': '',
            'company': '',
            'bio': '',
            'context': ''
        }

        try:
            # Extract name
            try:
                name_element = self.driver.find_element(
                    By.XPATH,
                    "//h1[contains(@class, 'text-heading-xlarge')]"
                )
                profile_data['name'] = name_element.text.strip()
            except NoSuchElementException:
                pass

            # Extract title
            try:
                title_element = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'text-body-medium') and contains(@class, 'break-words')]"
                )
                profile_data['title'] = title_element.text.strip()
            except NoSuchElementException:
                pass

            # Extract company (from experience section if visible)
            try:
                company_element = self.driver.find_element(
                    By.XPATH,
                    "//div[@id='experience']//following::span[contains(@class, 't-bold')]"
                )
                profile_data['company'] = company_element.text.strip()
            except NoSuchElementException:
                pass

            # Extract about/bio
            try:
                bio_element = self.driver.find_element(
                    By.XPATH,
                    "//div[@id='about']//following::div[contains(@class, 'display-flex')]//span[@aria-hidden='true']"
                )
                profile_data['bio'] = bio_element.text.strip()[:300]  # Limit length
            except NoSuchElementException:
                pass

        except Exception as e:
            utils.log(f"Error extracting profile data: {str(e)}", "WARNING")

        return profile_data

    def _simple_profile_analysis(self, profile_data):
        """
        Simple keyword-based profile analysis (fallback)

        Args:
            profile_data: Dict with profile information

        Returns:
            dict: Analysis results
        """
        title = profile_data.get('title', '').lower()
        bio = profile_data.get('bio', '').lower()
        combined = f"{title} {bio}"

        # Check for recruiter keywords
        recruiter_keywords = [
            'recruiter', 'talent acquisition', 'hiring', 'talent partner',
            'hr', 'headhunter', 'staffing', 'recruitment'
        ]
        is_recruiter = any(keyword in combined for keyword in recruiter_keywords)

        # Check for hiring manager keywords
        hiring_keywords = [
            'director', 'manager', 'head of', 'vp', 'vice president',
            'cto', 'ceo', 'lead', 'chief', 'founder'
        ]
        is_hiring_manager = any(keyword in combined for keyword in hiring_keywords)

        # Calculate connection value
        connection_value = 0.0
        if is_recruiter:
            connection_value = 0.9  # High value
        elif is_hiring_manager:
            connection_value = 0.7  # Good value
        elif 'engineer' in combined or 'developer' in combined:
            connection_value = 0.5  # Moderate value (peer)
        else:
            connection_value = 0.3  # Low value

        is_relevant = is_recruiter or is_hiring_manager or connection_value > 0.4

        return {
            'is_recruiter': is_recruiter,
            'is_hiring_manager': is_hiring_manager,
            'is_relevant': is_relevant,
            'connection_value': connection_value,
            'reasoning': 'Keyword-based analysis'
        }

    def is_recruiter(self, profile_url=None, profile_data=None):
        """
        Quick check if profile is a recruiter

        Args:
            profile_url: Profile URL (will navigate and analyze)
            profile_data: Pre-extracted profile data (faster)

        Returns:
            bool: True if recruiter
        """
        if profile_data:
            analysis = self._simple_profile_analysis(profile_data)
        elif profile_url:
            analysis = self.analyze_profile(profile_url)
        else:
            return False

        return analysis.get('is_recruiter', False)

    def is_hiring_manager(self, profile_url=None, profile_data=None):
        """
        Quick check if profile is a hiring manager

        Args:
            profile_url: Profile URL
            profile_data: Pre-extracted profile data

        Returns:
            bool: True if hiring manager
        """
        if profile_data:
            analysis = self._simple_profile_analysis(profile_data)
        elif profile_url:
            analysis = self.analyze_profile(profile_url)
        else:
            return False

        return analysis.get('is_hiring_manager', False)

    def calculate_connection_value(self, profile_url=None, profile_data=None):
        """
        Calculate the value of connecting with this person

        Args:
            profile_url: Profile URL
            profile_data: Pre-extracted profile data

        Returns:
            float: Connection value score (0.0-1.0)
        """
        if profile_data:
            analysis = self._simple_profile_analysis(profile_data)
        elif profile_url:
            analysis = self.analyze_profile(profile_url)
        else:
            return 0.0

        return analysis.get('connection_value', 0.0)

    def extract_profile_from_post(self, post_element):
        """
        Extract profile URL from a post element

        Args:
            post_element: Selenium WebElement for a post

        Returns:
            str: Profile URL or None
        """
        try:
            profile_link = post_element.find_element(
                By.XPATH,
                ".//a[contains(@href, '/in/')]"
            )
            return profile_link.get_attribute('href')
        except NoSuchElementException:
            return None

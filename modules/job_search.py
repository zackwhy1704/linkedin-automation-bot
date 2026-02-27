"""
LinkedIn Job Search Module

This module provides functionality to search for jobs on LinkedIn using Selenium.
It handles job search, result extraction, and filtering of new jobs.
"""

import logging
import time
from typing import List, Dict, Set, Callable, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

logger = logging.getLogger(__name__)


class LinkedInJobSearch:
    """
    Handles LinkedIn job search operations using Selenium WebDriver.
    """

    def __init__(self, driver: webdriver.Chrome):
        """
        Initialize the LinkedIn Job Search module.

        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def search_jobs(
        self,
        keywords: List[str],
        location: str,
        max_results: int = 50,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn with given keywords and location.

        Args:
            keywords: List of job search keywords (will be OR'ed together)
            location: Job location
            max_results: Maximum number of results to fetch
            progress_callback: Optional callback function for progress updates

        Returns:
            List of job dictionaries containing job details
        """
        try:
            # Join keywords with OR for LinkedIn search
            keyword_query = " OR ".join([f'"{kw}"' for kw in keywords]) if keywords else ""

            # Construct LinkedIn jobs search URL with sortBy=DD for newest first
            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword_query.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&sortBy=DD"
            )

            logger.info(f"Searching jobs with keywords: '{keyword_query}', location: '{location}'")
            if progress_callback:
                progress_callback(f"Searching: {keyword_query} in {location}")

            # Navigate to search URL
            self.driver.get(search_url)
            time.sleep(2)

            # Scroll to load more results
            self._scroll_to_load_results(max_results, progress_callback)

            # Extract job cards
            jobs = self._extract_job_cards(max_results)

            logger.info(f"Found {len(jobs)} jobs for keywords: '{keyword_query}'")
            if progress_callback:
                progress_callback(f"Found {len(jobs)} jobs")

            return jobs

        except Exception as e:
            logger.error(f"Error searching jobs: {e}", exc_info=True)
            if progress_callback:
                progress_callback(f"Error searching jobs: {e}")
            return []

    def _scroll_to_load_results(
        self,
        max_results: int,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Scroll the page to load more job results.

        Args:
            max_results: Maximum number of results to load
            progress_callback: Optional callback for progress updates
        """
        try:
            scroll_pause_time = 1.5
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = max_results // 25 + 2  # LinkedIn loads ~25 jobs per scroll

            while scroll_attempts < max_scrolls:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)

                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                # Check if reached bottom
                if new_height == last_height:
                    logger.debug("Reached bottom of job listings")
                    break

                last_height = new_height
                scroll_attempts += 1

                if progress_callback and scroll_attempts % 2 == 0:
                    progress_callback(f"Loading more results... (scroll {scroll_attempts})")

        except Exception as e:
            logger.warning(f"Error during scrolling: {e}")

    def _extract_job_cards(self, max_results: int) -> List[Dict[str, Any]]:
        """
        Extract job card elements from the page and parse their data.

        Args:
            max_results: Maximum number of job cards to extract

        Returns:
            List of job dictionaries
        """
        jobs = []

        try:
            # Wait for job list to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-search__results-list, div.jobs-search-results-list"))
            )
            time.sleep(1)

            # Try multiple CSS selectors to find job cards
            job_card_selectors = [
                "li.jobs-search-results__list-item",
                "div.job-card-container",
                "div.jobs-search-results__list-item",
                "li.jobs-search-results-list__list-item",
                "div.scaffold-layout__list-item"
            ]

            job_cards = []
            for selector in job_card_selectors:
                try:
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if job_cards:
                        logger.debug(f"Found {len(job_cards)} job cards using selector: {selector}")
                        break
                except NoSuchElementException:
                    continue

            if not job_cards:
                logger.warning("No job cards found with any selector")
                return []

            # Extract data from each card
            for i, card in enumerate(job_cards[:max_results]):
                if i >= max_results:
                    break

                try:
                    job_data = self._extract_card_data(card)
                    if job_data and job_data.get('job_id'):
                        jobs.append(job_data)
                except Exception as e:
                    logger.warning(f"Error extracting data from job card {i}: {e}")
                    continue

        except TimeoutException:
            logger.error("Timeout waiting for job list to load")
        except Exception as e:
            logger.error(f"Error extracting job cards: {e}", exc_info=True)

        return jobs

    def _extract_card_data(self, card) -> Optional[Dict[str, Any]]:
        """
        Extract job data from a single job card element.

        Args:
            card: Selenium WebElement representing a job card

        Returns:
            Dictionary containing job details or None if extraction fails
        """
        try:
            job_data = {}

            # Extract job_id from data-job-id attribute or URL
            job_id = None
            try:
                job_id = card.get_attribute('data-job-id')
            except Exception:
                pass

            if not job_id:
                try:
                    # Try to extract from link href
                    link_element = card.find_element(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
                    href = link_element.get_attribute('href')
                    if href and '/jobs/view/' in href:
                        job_id = href.split('/jobs/view/')[1].split('/')[0].split('?')[0]
                except Exception:
                    pass

            if not job_id:
                logger.debug("Could not extract job_id from card")
                return None

            job_data['job_id'] = job_id

            # Extract title
            title = None
            title_selectors = [
                ".base-search-card__title",
                ".job-card-list__title",
                ".job-card-container__link",
                "h3.base-search-card__title",
                "a.job-card-list__title"
            ]

            for selector in title_selectors:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue

            job_data['title'] = title or "Unknown Title"

            # Extract company
            company = None
            company_selectors = [
                ".base-search-card__subtitle",
                ".job-card-container__company-name",
                "h4.base-search-card__subtitle",
                "a.job-card-container__link--company"
            ]

            for selector in company_selectors:
                try:
                    company_element = card.find_element(By.CSS_SELECTOR, selector)
                    company = company_element.text.strip()
                    if company:
                        break
                except NoSuchElementException:
                    continue

            job_data['company'] = company or "Unknown Company"

            # Extract location
            location = None
            location_selectors = [
                ".job-search-card__location",
                ".job-card-container__metadata-item",
                "span.job-search-card__location",
                ".base-search-card__metadata"
            ]

            for selector in location_selectors:
                try:
                    location_element = card.find_element(By.CSS_SELECTOR, selector)
                    location = location_element.text.strip()
                    if location:
                        break
                except NoSuchElementException:
                    continue

            job_data['location'] = location or "Unknown Location"

            # Extract posted time
            posted_text = None
            try:
                time_element = card.find_element(By.CSS_SELECTOR, "time")
                posted_text = time_element.get_attribute('datetime') or time_element.text.strip()
            except NoSuchElementException:
                try:
                    # Alternative: look for text containing time info
                    posted_element = card.find_element(By.CSS_SELECTOR, ".job-search-card__listdate")
                    posted_text = posted_element.text.strip()
                except NoSuchElementException:
                    pass

            job_data['posted_text'] = posted_text or "Unknown"

            # Build job URL
            job_data['job_url'] = f"https://www.linkedin.com/jobs/view/{job_id}/"

            logger.debug(f"Extracted job: {job_data['title']} at {job_data['company']}")
            return job_data

        except StaleElementReferenceException:
            logger.warning("Stale element reference while extracting card data")
            return None
        except Exception as e:
            logger.warning(f"Error extracting card data: {e}")
            return None

    def filter_new_jobs(self, jobs: List[Dict[str, Any]], seen_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Filter jobs to exclude those already seen.

        Args:
            jobs: List of job dictionaries
            seen_ids: Set of job IDs that have been seen before

        Returns:
            List of new jobs not in seen_ids
        """
        if not seen_ids:
            return jobs

        new_jobs = [job for job in jobs if job.get('job_id') not in seen_ids]

        logger.info(f"Filtered {len(jobs)} jobs to {len(new_jobs)} new jobs")
        return new_jobs

    def get_all_search_keywords(self, config: Dict[str, Any]) -> List[str]:
        """
        Get all search keywords from configuration.

        Combines target_roles, scan_keywords, and resume_keywords from config.

        Args:
            config: Configuration dictionary containing keyword lists

        Returns:
            List of unique search keywords
        """
        keywords = []

        # Add target roles
        target_roles = config.get('target_roles', [])
        if isinstance(target_roles, list):
            keywords.extend(target_roles)

        # Add scan keywords
        scan_keywords = config.get('scan_keywords', [])
        if isinstance(scan_keywords, list):
            keywords.extend(scan_keywords)

        # Add resume keywords
        resume_keywords = config.get('resume_keywords', [])
        if isinstance(resume_keywords, list):
            keywords.extend(resume_keywords)

        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword and keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)

        logger.info(f"Generated {len(unique_keywords)} unique search keywords from config")
        return unique_keywords

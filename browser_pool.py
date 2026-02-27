#!/usr/bin/env python3
"""
Browser Pool Manager
Manages a pool of Chrome browser instances for concurrent users
Provides session isolation and reuse to optimize resource usage
"""

import threading
from queue import Queue, Empty
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class BrowserContext:
    """Represents a browser instance with session state"""
    driver: webdriver.Chrome
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    user_id: int = None  # Currently assigned user
    is_logged_in: bool = False
    last_used: datetime = None
    usage_count: int = 0

    def mark_logged_in(self):
        """Mark browser as logged in for current user"""
        self.is_logged_in = True
        self.last_used = datetime.now()

    def is_stale(self, max_idle_minutes: int = 30):
        """Check if browser session is stale"""
        if not self.last_used:
            return False
        return datetime.now() - self.last_used > timedelta(minutes=max_idle_minutes)

    def needs_refresh(self, max_usage: int = 50):
        """Check if browser needs to be recreated"""
        return self.usage_count >= max_usage


class BrowserPool:
    """
    Manages a pool of Chrome browser instances for concurrent users

    Features:
    - Per-user session isolation
    - Automatic session recovery
    - Browser recycling
    - Resource limits
    - Thread-safe operations
    """

    def __init__(self, max_browsers: int = 5, headless: bool = True):
        """
        Initialize browser pool

        Args:
            max_browsers: Maximum number of concurrent browser instances
            headless: Whether to run Chrome in headless mode
        """
        self.max_browsers = max_browsers
        self.headless = headless

        # Thread-safe structures
        self.available = Queue(maxsize=max_browsers)
        self.in_use = {}  # {browser_id: BrowserContext}
        self.user_sessions = {}  # {user_id: browser_id}

        self.lock = threading.Lock()
        self.browser_id_counter = 0

        logger.info(f"BrowserPool initialized: max_browsers={max_browsers}, headless={headless}")

    def _create_browser(self) -> webdriver.Chrome:
        """Create new Chrome browser instance with anti-detection measures"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Performance optimizations
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")

        # Memory limits
        chrome_options.add_argument("--max-old-space-size=512")

        # Create driver
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            raise

        # Anti-detection scripts
        try:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent").replace("Headless", "")
            })
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            logger.warning(f"Failed to apply anti-detection measures: {e}")

        logger.info("Created new Chrome browser instance")
        return driver

    def acquire(self, user_id: int, timeout: int = 60) -> BrowserContext:
        """
        Acquire a browser for a user

        Args:
            user_id: User's Telegram ID
            timeout: Max wait time in seconds

        Returns:
            BrowserContext ready for use

        Raises:
            RuntimeError: If browser pool is exhausted
        """
        with self.lock:
            # Check if user already has a session
            if user_id in self.user_sessions:
                browser_id = self.user_sessions[user_id]
                if browser_id in self.in_use:
                    context = self.in_use[browser_id]

                    # Validate session
                    if not context.is_stale():
                        context.usage_count += 1
                        context.last_used = datetime.now()
                        logger.info(f"Reusing existing session for user {user_id} (browser {context.session_id})")
                        return context
                    else:
                        # Session stale, clean up
                        logger.warning(f"Stale session for user {user_id}, recreating")
                        self._close_browser_context(context)

            # Try to get available browser
            try:
                context = self.available.get(timeout=timeout)
                logger.info(f"Reused available browser {context.session_id} for user {user_id}")
            except Empty:
                # No available browser, check if we can create new
                if len(self.in_use) < self.max_browsers:
                    driver = self._create_browser()
                    self.browser_id_counter += 1
                    context = BrowserContext(
                        driver=driver,
                        session_id=f"browser_{self.browser_id_counter}"
                    )
                    logger.info(f"Created new browser {context.session_id} for user {user_id}")
                else:
                    raise RuntimeError(
                        f"Browser pool exhausted ({self.max_browsers} browsers in use). "
                        "Please try again later."
                    )

            # Assign to user
            context.user_id = user_id
            context.last_used = datetime.now()
            context.usage_count += 1

            self.in_use[context.session_id] = context
            self.user_sessions[user_id] = context.session_id

            return context

    def release(self, context: BrowserContext):
        """
        Release browser back to pool

        Args:
            context: Browser context to release
        """
        with self.lock:
            if context.session_id not in self.in_use:
                logger.warning(f"Attempted to release unknown browser {context.session_id}")
                return

            # Check if browser needs refresh
            if context.needs_refresh():
                logger.info(f"Browser {context.session_id} reached usage limit, closing")
                self._close_browser_context(context)
                return

            # Clean browser state (but preserve session)
            try:
                # Navigate to blank page
                context.driver.get("about:blank")

                # Clear user assignment but keep login state
                context.user_id = None
                context.last_used = datetime.now()

                # Return to pool
                del self.in_use[context.session_id]
                self.available.put(context)

                logger.info(f"Browser {context.session_id} released to pool")

            except Exception as e:
                logger.error(f"Error releasing browser {context.session_id}: {e}")
                self._close_browser_context(context)

    def _close_browser_context(self, context: BrowserContext):
        """Safely close and cleanup browser context"""
        try:
            context.driver.quit()

            if context.session_id in self.in_use:
                del self.in_use[context.session_id]

            if context.user_id and context.user_id in self.user_sessions:
                del self.user_sessions[context.user_id]

            logger.info(f"Closed browser {context.session_id}")

        except Exception as e:
            logger.error(f"Error closing browser {context.session_id}: {e}")

    def cleanup_stale_sessions(self):
        """Background task to clean up stale sessions"""
        with self.lock:
            stale_contexts = [
                ctx for ctx in self.in_use.values()
                if ctx.is_stale()
            ]

            for ctx in stale_contexts:
                logger.info(f"Cleaning up stale browser {ctx.session_id}")
                self._close_browser_context(ctx)

    def shutdown(self):
        """Shutdown all browsers in pool"""
        with self.lock:
            # Close all in-use browsers
            for context in list(self.in_use.values()):
                self._close_browser_context(context)

            # Close available browsers
            while not self.available.empty():
                try:
                    context = self.available.get_nowait()
                    self._close_browser_context(context)
                except Empty:
                    break

            logger.info("BrowserPool shutdown complete")

    def get_stats(self):
        """Get browser pool statistics"""
        with self.lock:
            return {
                'max_browsers': self.max_browsers,
                'in_use': len(self.in_use),
                'available': self.available.qsize(),
                'active_users': len(self.user_sessions),
                'total_created': self.browser_id_counter
            }


# Global browser pool (one per worker process)
_browser_pool = None


def get_browser_pool() -> BrowserPool:
    """Get or create the global browser pool"""
    global _browser_pool
    if _browser_pool is None:
        max_browsers = int(os.getenv('BROWSER_POOL_SIZE', 5))
        headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        _browser_pool = BrowserPool(max_browsers=max_browsers, headless=headless)
    return _browser_pool


def shutdown_browser_pool():
    """Shutdown the global browser pool"""
    global _browser_pool
    if _browser_pool is not None:
        _browser_pool.shutdown()
        _browser_pool = None

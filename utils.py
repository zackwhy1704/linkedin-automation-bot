import random
import time
import os
from datetime import datetime
from fake_useragent import UserAgent

def random_delay(min_delay=2, max_delay=5):
    """Add random delay to mimic human behavior"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def sanitize_for_chrome(text):
    """
    Remove characters outside Basic Multilingual Plane (BMP) that ChromeDriver can't handle
    BMP includes characters from U+0000 to U+FFFF
    """
    # Filter out characters outside BMP (ord > 0xFFFF)
    return ''.join(char for char in text if ord(char) <= 0xFFFF)

def human_type(element, text, typing_speed=0.1, use_javascript=False):
    """
    Type text with human-like delays

    Args:
        element: WebElement to type into
        text: Text to type
        typing_speed: Maximum delay between characters
        use_javascript: If True, use JavaScript to set content (bypasses BMP limitation)
    """
    try:
        if use_javascript:
            # Use JavaScript to set content (bypasses ChromeDriver BMP limitation)
            driver = element.parent
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].textContent = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, element, text)
            time.sleep(random.uniform(0.5, 1.0))
        else:
            # Sanitize text to remove non-BMP characters
            sanitized_text = sanitize_for_chrome(text)
            if sanitized_text != text:
                log(f"Warning: Removed {len(text) - len(sanitized_text)} non-BMP characters from text", "WARNING")

            # Type character by character
            for char in sanitized_text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, typing_speed))

    except Exception as e:
        # If typing fails, fallback to JavaScript method
        log(f"human_type failed with send_keys, trying JavaScript fallback: {e}", "WARNING")
        try:
            driver = element.parent
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].textContent = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, element, text)
        except Exception as js_error:
            log(f"JavaScript fallback also failed: {js_error}", "ERROR")
            raise

def scroll_slowly(driver, scroll_pause_time=0.5):
    """Scroll page slowly to mimic human behavior"""
    screen_height = driver.execute_script("return window.screen.height;")
    i = 1

    while True:
        driver.execute_script(f"window.scrollTo(0, {screen_height}*{i});")
        i += 1
        time.sleep(scroll_pause_time)

        scroll_height = driver.execute_script("return document.body.scrollHeight;")
        if (screen_height) * i > scroll_height:
            break

def get_random_user_agent():
    """Get random user agent"""
    ua = UserAgent()
    return ua.random

def log(message, level="INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def ensure_directory(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def random_choice_weighted(choices, weights):
    """Make weighted random choice"""
    return random.choices(choices, weights=weights, k=1)[0]

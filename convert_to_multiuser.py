#!/usr/bin/env python3
"""
Script to convert telegram_bot.py to use Celery tasks for multi-user support
This replaces Thread() calls with task.delay() calls
"""

import re

def convert_to_multiuser():
    """Convert telegram bot to use Celery tasks"""

    # Read the original file
    with open('telegram_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace import
    content = content.replace(
        'from threading import Thread',
        '# Multi-user: Use Celery instead of threading\n# from threading import Thread'
    )

    # Add Celery task imports after other imports
    import_section = content.find('import uuid')
    if import_section != -1:
        content = content[:import_section] + '''import uuid

# Celery tasks for multi-user support
try:
    from tasks import (
        post_to_linkedin_task,
        engage_with_feed_task,
        reply_engagement_task,
        send_connection_requests_task,
        autopilot_task,
        scan_jobs_task
    )
    CELERY_ENABLED = True
    print("[INFO] Celery tasks loaded - Multi-user mode enabled")
except ImportError as e:
    CELERY_ENABLED = False
    print(f"[WARNING] Celery tasks not available: {e}")
    print("[WARNING] Falling back to single-user threading mode")
    from threading import Thread

''' + content[import_section + len('import uuid'):]

    # 2. Replace Thread calls with task.delay() calls
    replacements = [
        # Autopilot
        (
            r'Thread\(target=run_autopilot, args=\(telegram_id,\)\)\.start\(\)',
            '''if CELERY_ENABLED:
        autopilot_task.delay(telegram_id)
    else:
        Thread(target=run_autopilot, args=(telegram_id,)).start()'''
        ),
        # Reply engagement
        (
            r'Thread\(target=run_reply_engagement, args=\(telegram_id,\)\)\.start\(\)',
            '''if CELERY_ENABLED:
        reply_engagement_task.delay(telegram_id, max_replies=5)
    else:
        Thread(target=run_reply_engagement, args=(telegram_id,)).start()'''
        ),
        # Feed engagement
        (
            r'Thread\(target=run_engagement, args=\(telegram_id,\)\)\.start\(\)',
            '''if CELERY_ENABLED:
        engage_with_feed_task.delay(telegram_id, max_engagements=10)
    else:
        Thread(target=run_engagement, args=(telegram_id,)).start()'''
        ),
        # Connection requests
        (
            r'Thread\(target=run_connection_requests, args=\(telegram_id,\)\)\.start\(\)',
            '''if CELERY_ENABLED:
        send_connection_requests_task.delay(telegram_id, count=10)
    else:
        Thread(target=run_connection_requests, args=(telegram_id,)).start()'''
        ),
        # Post visible browser
        (
            r'Thread\(target=run_post_visible_browser, args=\(telegram_id, generated_post\)\)\.start\(\)',
            '''if CELERY_ENABLED:
        post_to_linkedin_task.delay(telegram_id, generated_post)
    else:
        Thread(target=run_post_visible_browser, args=(telegram_id, generated_post)).start()'''
        ),
        # Job scan (multiple occurrences)
        (
            r'Thread\(target=run_job_scan, args=\((?:user\[\'telegram_id\'\]|telegram_id),\), daemon=True\)\.start\(\)',
            '''if CELERY_ENABLED:
        scan_jobs_task.delay(telegram_id)
    else:
        Thread(target=run_job_scan, args=(telegram_id,), daemon=True).start()'''
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # 3. Add comment to run_* functions indicating they're fallback
    content = content.replace(
        'def run_autopilot(telegram_id: int):',
        '''def run_autopilot(telegram_id: int):
    """
    Legacy threading function - used only if Celery is unavailable
    For multi-user mode, use autopilot_task.delay() instead
    """'''
    )

    content = content.replace(
        'def run_reply_engagement(telegram_id: int):',
        '''def run_reply_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""'''
    )

    content = content.replace(
        'def run_engagement(telegram_id: int):',
        '''def run_engagement(telegram_id: int):
    """Legacy threading function - fallback only"""'''
    )

    content = content.replace(
        'def run_connection_requests(telegram_id: int):',
        '''def run_connection_requests(telegram_id: int):
    """Legacy threading function - fallback only"""'''
    )

    content = content.replace(
        'def run_post_visible_browser(telegram_id: int, generated_post: str):',
        '''def run_post_visible_browser(telegram_id: int, generated_post: str):
    """Legacy threading function - fallback only"""'''
    )

    content = content.replace(
        'def run_job_scan(telegram_id: int):',
        '''def run_job_scan(telegram_id: int):
    """Legacy threading function - fallback only"""'''
    )

    # Write to multiuser version
    with open('multiuser/telegram_bot_multiuser.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("[OK] Conversion complete!")
    print("[OK] Created: multiuser/telegram_bot_multiuser.py")
    print("\nThis version:")
    print("  - Uses Celery tasks when available (multi-user mode)")
    print("  - Falls back to threading if Celery not available (single-user mode)")
    print("  - Maintains backward compatibility")


if __name__ == "__main__":
    convert_to_multiuser()

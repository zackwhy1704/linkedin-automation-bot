# Fix Asyncio Event Loop Error in Background Workers

## Problem
Background workers are using `asyncio.run(bot.send_message(...))` which creates conflicts with the main event loop.

## Solution
Remove all `asyncio.run()` calls from background workers and use logging instead. The main thread will show status updates.

## Changes Needed

### 1. run_autopilot (4 calls)
- Remove credential check message
- Remove login failure message
- Remove success summary message
- Remove error message

### 2. run_engagement (4 calls)
- Remove credential check message
- Remove login failure message
- Remove success summary message
- Remove error message

### 3. run_reply_engagement (4 calls)
- Remove credential check message
- Remove login failure message
- Remove success summary message
- Remove error message

### 4. run_connection_requests (4 calls)
- Remove credential check message
- Remove login failure message
- Remove success summary message
- Remove error message

### 5. run_post_visible_browser (0 calls - FIXED)
- ✅ Already fixed

## Alternative: Use Queue-Based Messaging

For future improvement, implement a message queue where workers add messages and main thread sends them:

```python
from queue import Queue
message_queue = Queue()

# In worker:
message_queue.put((telegram_id, "Message text"))

# In main thread (periodic check):
while not message_queue.empty():
    chat_id, text = message_queue.get()
    await bot.send_message(chat_id=chat_id, text=text)
```

## Quick Fix Script

Run this to remove all asyncio.run calls from workers and replace with logger.info:
```bash
# Backup first
cp telegram_bot.py telegram_bot.py.backup

# Then manually edit the 4 worker functions
```

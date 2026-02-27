#!/usr/bin/env python3
"""
Celery Application Configuration
Manages distributed task queue for multi-user LinkedIn automation
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from celery import Celery
from kombu import Queue, Exchange

# Initialize Celery app
app = Celery('linkedin_automation', include=['tasks'])

# Redis broker configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.conf.broker_url = REDIS_URL
app.conf.result_backend = REDIS_URL

# Task routing and prioritization
default_exchange = Exchange('default', type='direct')
posting_exchange = Exchange('posting', type='direct')
engagement_exchange = Exchange('engagement', type='direct')
connections_exchange = Exchange('connections', type='direct')
notifications_exchange = Exchange('notifications', type='direct')

app.conf.task_queues = (
    Queue('posting', posting_exchange, routing_key='posting.#', priority=10),
    Queue('engagement', engagement_exchange, routing_key='engagement.#', priority=5),
    Queue('connections', connections_exchange, routing_key='connections.#', priority=3),
    Queue('job_search', default_exchange, routing_key='job_search.#', priority=1),
    Queue('notifications', notifications_exchange, routing_key='notifications.#', priority=8),
)

app.conf.task_routes = {
    'tasks.post_to_linkedin_task': {'queue': 'posting', 'routing_key': 'posting.create'},
    'tasks.engage_with_feed_task': {'queue': 'engagement', 'routing_key': 'engagement.feed'},
    'tasks.reply_engagement_task': {'queue': 'engagement', 'routing_key': 'engagement.reply'},
    'tasks.send_connection_requests_task': {'queue': 'connections', 'routing_key': 'connections.send'},
    'tasks.autopilot_task': {'queue': 'posting', 'routing_key': 'posting.autopilot'},
    'tasks.scan_jobs_task': {'queue': 'job_search', 'routing_key': 'job_search.scan'},
    'tasks.send_telegram_notification': {'queue': 'notifications', 'routing_key': 'notifications.send'},
}

# Worker configuration
app.conf.worker_prefetch_multiplier = 1  # One task per worker at a time (browser-heavy)
app.conf.worker_max_tasks_per_child = 50  # Restart worker after 50 tasks (prevent memory leaks)
app.conf.task_acks_late = True  # Acknowledge task only after completion
app.conf.task_reject_on_worker_lost = True  # Re-queue if worker crashes

# Task timeouts
app.conf.task_time_limit = 600  # 10 minutes hard limit
app.conf.task_soft_time_limit = 540  # 9 minutes soft limit (graceful)

# Result expiration
app.conf.result_expires = 3600  # 1 hour

# Serialization
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Retry configuration
app.conf.task_default_retry_delay = 60  # 1 minute default retry delay
app.conf.task_max_retries = 3  # Maximum 3 retries

# Logging
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'

# Task always eager (for testing - set to False in production)
app.conf.task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true'

if __name__ == '__main__':
    app.start()

"""
Facebook Bot Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Facebook credentials
PAGE_ACCESS_TOKEN = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('FACEBOOK_VERIFY_TOKEN')
PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')

# Agent info
AGENT_NAME = os.getenv('AGENT_NAME', 'Property Agent')
AGENT_PHONE = os.getenv('AGENT_PHONE', '+65 XXXX XXXX')

# Bot behavior
MAX_DMS_PER_MINUTE = 20
TYPING_DELAY_SECONDS = 1.5
HUMAN_DELAY_MIN = 0.5
HUMAN_DELAY_MAX = 2.0

# Database
DATABASE_URL = f"postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_NAME')}"

# Telegram (for agent alerts)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AGENT_TELEGRAM_ID = os.getenv('AGENT_TELEGRAM_ID')  # Agent's Telegram user ID

# AI Service
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Trigger keywords for comment auto-reply
COMMENT_TRIGGERS = [
    'price', 'cost', 'how much', 'available', 'interested',
    'details', 'contact', 'info', 'agent', 'viewing',
    'location', 'floor plan', 'units', 'listing', 'sell',
    'buy', 'invest', 'valuation', 'book', 'appointment'
]

# Property types
PROPERTY_TYPES = ['HDB', 'Condo', 'Landed', 'Commercial']

# Budget ranges (in SGD)
BUDGET_RANGES = {
    '1': {'min': 0, 'max': 600000, 'label': 'Under $600K'},
    '2': {'min': 600000, 'max': 1000000, 'label': '$600K – $1M'},
    '3': {'min': 1000000, 'max': 2000000, 'label': '$1M – $2M'},
    '4': {'min': 2000000, 'max': 999999999, 'label': 'Above $2M'},
}

# Timeline options
TIMELINES = {
    '1': 'urgent',           # 1-3 months
    '2': '3-6mo',
    '3': '6-12mo',
    '4': 'exploring',
}

# Lead scoring weights
LEAD_SCORE_WEIGHTS = {
    'intent_buy': 3,
    'intent_sell': 3,
    'intent_invest': 3,
    'intent_browse': 1,
    'timeline_urgent': 3,
    'timeline_3_6mo': 2,
    'timeline_6_12mo': 1,
    'timeline_exploring': 0,
    'budget_high': 3,        # >$1.2M
    'budget_mid': 2,          # $600K-$1.2M
    'budget_low': 1,          # <$600K
    'phone_provided': 2,
    'email_provided': 1,
    'direct_dm': 1,
}

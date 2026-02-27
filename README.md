# LinkedIn Automation Bot

**For Educational and Testing Purposes Only**

A Python-based LinkedIn automation bot that can handle scheduled posting, auto-replies, feed engagement, and private messaging.

## Warning

This bot uses browser automation to interact with LinkedIn, which **violates LinkedIn's Terms of Service**. Use at your own risk on test accounts only. Your account may be:
- Suspended
- Permanently banned
- Flagged for suspicious activity

**DO NOT use this on your primary professional LinkedIn account.**

## Features

- **Scheduled Posting**: Schedule posts with custom content and media
- **Auto-Reply**: Automatically reply to comments on your posts
- **Feed Engagement**: Like and comment on posts in your feed
- **Keyword Search**: Search for specific keywords and engage with matching posts
- **Private Messaging**: Send messages and connection requests
- **Message Auto-Response**: Automatically respond to incoming messages
- **Anti-Detection**: Human-like delays and randomized actions

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- A LinkedIn test account (not your primary account!)

## Installation

1. Clone or download this repository

2. Navigate to the project directory:
```bash
cd linkedin-automation-bot
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create your environment file:
```bash
copy .env.example .env
```

5. Edit `.env` and add your LinkedIn credentials:
```
LINKEDIN_EMAIL=your_test_account@example.com
LINKEDIN_PASSWORD=your_password
HEADLESS=False
```

## Configuration

### Scheduled Posts

Edit `data/posts_template.json` to add your scheduled posts:

```json
[
  {
    "id": 1,
    "content": "Your post content here",
    "schedule_time": "2026-02-10 09:00:00",
    "media": null,
    "posted": false
  }
]
```

### Reply Templates

Edit `data/reply_templates.json` to customize auto-replies:

```json
{
  "generic_replies": [
    "Thanks for your comment!",
    "I appreciate your input!"
  ],
  "keyword_based": {
    "great": "Thank you! Glad you liked it!"
  }
}
```

### Engagement Settings

Edit `data/engagement_config.json` to configure engagement preferences:

```json
{
  "hashtags_to_follow": ["#python", "#coding"],
  "engagement_preferences": {
    "like_probability": 0.7,
    "comment_probability": 0.3
  }
}
```

## Usage

### Interactive Mode

Run the bot in interactive mode for manual control:

```bash
python main.py
```

This will show you a menu with options:
1. Create a single post
2. Check and post scheduled posts
3. Engage with feed (likes/comments)
4. Search and engage with keyword
5. Reply to comments
6. Send a message
7. Send connection request
8. Check messages
9. Run all automated tasks once
0. Exit

### Scheduled Mode

Run the bot in scheduled mode for automatic operation:

```bash
python scheduler.py
```

The scheduler will:
- Check for scheduled posts every 30 minutes
- Engage with feed at 9:00 AM and 5:00 PM daily
- Reply to comments at 10:00 AM, 2:00 PM, and 6:00 PM daily
- Check messages every 2 hours

Press `Ctrl+C` to stop the scheduler.

## Project Structure

```
linkedin-automation-bot/
├── linkedin_bot.py           # Main bot class
├── main.py                   # Interactive mode entry point
├── scheduler.py              # Scheduled automation runner
├── utils.py                  # Helper functions
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore file
├── README.md                # This file
├── modules/                 # Bot modules
│   ├── __init__.py
│   ├── login.py            # Login automation
│   ├── posting.py          # Post creation and scheduling
│   ├── auto_reply.py       # Auto-reply to comments
│   ├── engagement.py       # Feed engagement
│   └── messaging.py        # Private messaging
└── data/                    # Configuration and data files
    ├── posts_template.json
    ├── reply_templates.json
    └── engagement_config.json
```

## Anti-Detection Features

The bot includes several anti-detection measures:

1. **Random Delays**: Human-like delays between actions (2-5 seconds)
2. **Human Typing**: Simulates human typing speed with character-by-character input
3. **Randomized Actions**: Random probability for liking vs commenting
4. **User Agent Rotation**: Uses random user agents
5. **WebDriver Hiding**: Hides automation indicators from the browser
6. **Slow Scrolling**: Mimics human scrolling behavior

## Safety Limits

Built-in safety limits to prevent excessive activity:

- Max 20 likes per session
- Max 10 comments per session
- Max 5 messages per session
- 2-5 second delays between actions
- 5-10 second delays between posts

You can adjust these in the `.env` file.

## Troubleshooting

### Login Issues

If you encounter login issues:
1. Make sure your credentials are correct in `.env`
2. Try with `HEADLESS=False` to see what's happening
3. LinkedIn may require 2FA - complete it manually when prompted
4. Wait a few hours and try again if you've been rate-limited

### Element Not Found Errors

LinkedIn frequently updates their UI, which may break the bot. If you get element not found errors:
1. Check if LinkedIn has updated their interface
2. You may need to update the XPath selectors in the module files
3. Run with `HEADLESS=False` to debug visually

### Rate Limiting

If the bot is detected or rate-limited:
1. Increase delays in the `.env` file
2. Reduce the number of actions per session
3. Add longer pauses between different types of actions
4. Consider using the bot less frequently

## Customization

You can extend the bot by:

1. Adding new modules in the `modules/` directory
2. Creating custom engagement strategies
3. Implementing more sophisticated reply logic
4. Adding image/video posting capabilities
5. Integrating with external APIs for content generation

## Disclaimer

This project is for **educational purposes only**. The author is not responsible for:
- Account suspensions or bans
- Violation of LinkedIn's Terms of Service
- Any consequences of using this bot
- Spam or unwanted messages sent by users of this bot

Use responsibly and only on test accounts.

## License

This project is provided as-is for educational purposes. Use at your own risk.

## Contributing

This is an educational project. Feel free to fork and modify for your own learning purposes.

## Support

This is an educational project with no official support. For issues:
1. Check the troubleshooting section
2. Review LinkedIn's current UI structure
3. Adjust the code for any LinkedIn updates

---

**Remember: Use this bot ethically and responsibly. Always respect LinkedIn's Terms of Service and other users' privacy.**

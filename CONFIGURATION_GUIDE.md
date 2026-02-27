# Configuration Guide

Complete guide to configuring your LinkedIn automation bot.

## Environment Variables (.env)

### Required Settings

```env
# Your LinkedIn credentials (USE TEST ACCOUNT ONLY)
LINKEDIN_EMAIL=your_test_account@example.com
LINKEDIN_PASSWORD=your_password
```

### Optional Settings

```env
# Browser Settings
HEADLESS=False                    # True = run browser in background, False = show browser
BROWSER=chrome                    # Currently only Chrome is supported

# Timing Settings (in seconds)
MIN_DELAY=2                       # Minimum delay between actions
MAX_DELAY=5                       # Maximum delay between actions
SCROLL_DELAY=1                    # Delay while scrolling

# Engagement Limits
MAX_LIKES_PER_SESSION=20          # Maximum likes in one session
MAX_COMMENTS_PER_SESSION=10       # Maximum comments in one session
MAX_MESSAGES_PER_SESSION=5        # Maximum messages in one session

# Safety Features
RANDOMIZE_ACTIONS=True            # Randomize action order
USE_HUMAN_DELAYS=True             # Use human-like delays
```

## Scheduled Posts (data/posts_template.json)

Configure posts to be automatically published at specific times.

### Format

```json
[
  {
    "id": 1,                                    // Unique post ID
    "content": "Your post text here",          // Post content (supports hashtags)
    "schedule_time": "2026-02-10 09:00:00",   // When to post (YYYY-MM-DD HH:MM:SS)
    "media": null,                             // Path to image/video (optional)
    "posted": false                            // Auto-updated when posted
  }
]
```

### Tips

- Use future dates for `schedule_time`
- The bot checks every 30 minutes by default
- Set `media` to full path if you want to attach images: `"C:\\path\\to\\image.jpg"`
- The `posted` flag prevents duplicate posts
- Keep posts professional and avoid spam

### Example

```json
[
  {
    "id": 1,
    "content": "Just completed a great Python project! Loving the automation possibilities. #Python #Coding #Developer",
    "schedule_time": "2026-02-10 09:00:00",
    "media": null,
    "posted": false
  },
  {
    "id": 2,
    "content": "Sharing my thoughts on web development best practices. What are your must-follow rules? #WebDev #JavaScript",
    "schedule_time": "2026-02-10 14:00:00",
    "media": "C:\\Users\\YourName\\Pictures\\webdev.png",
    "posted": false
  }
]
```

## Reply Templates (data/reply_templates.json)

Configure automatic replies to comments on your posts.

### Format

```json
{
  "generic_replies": [
    "Array of generic replies used when no keyword match"
  ],
  "question_replies": [
    "Replies used when comment contains '?'"
  ],
  "positive_replies": [
    "Replies for positive comments"
  ],
  "keyword_based": {
    "keyword": "Reply for this specific keyword"
  }
}
```

### How It Works

1. Bot checks for keywords first (`keyword_based`)
2. If comment has `?`, uses `question_replies`
3. If comment has positive words, uses `positive_replies`
4. Otherwise uses `generic_replies`
5. Randomly selects from matching category

### Example

```json
{
  "generic_replies": [
    "Thanks for your comment!",
    "I appreciate your input!",
    "Great point!",
    "Thanks for sharing!"
  ],
  "question_replies": [
    "That's a great question! Let me get back to you on that.",
    "Interesting question! I'll share more details soon."
  ],
  "positive_replies": [
    "Thank you so much!",
    "I really appreciate that!",
    "Glad you found it helpful!"
  ],
  "keyword_based": {
    "great": "Thank you! Glad you liked it!",
    "interesting": "Thanks! Happy you found it interesting!",
    "python": "Python is amazing, right? Let me know if you want to discuss more!",
    "helpful": "Glad I could help!"
  }
}
```

## Engagement Configuration (data/engagement_config.json)

Configure which content to engage with and how.

### Format

```json
{
  "hashtags_to_follow": [
    "#hashtag1",
    "#hashtag2"
  ],
  "keywords_to_engage": [
    "keyword1",
    "keyword2"
  ],
  "engagement_preferences": {
    "like_probability": 0.7,      // 70% chance to like a post
    "comment_probability": 0.3,    // 30% chance to comment
    "generic_comments": [
      "Array of generic comments"
    ]
  }
}
```

### Tips

- Choose hashtags relevant to your industry
- Use keywords to find relevant content
- Adjust probabilities to control engagement style
- Keep comments professional and genuine

### Example

```json
{
  "hashtags_to_follow": [
    "#python",
    "#javascript",
    "#webdevelopment",
    "#machinelearning",
    "#coding",
    "#programming"
  ],
  "keywords_to_engage": [
    "automation",
    "developer",
    "software engineer",
    "python developer"
  ],
  "engagement_preferences": {
    "like_probability": 0.8,
    "comment_probability": 0.2,
    "generic_comments": [
      "Great post!",
      "Very insightful!",
      "Thanks for sharing!",
      "Interesting perspective!",
      "Well said!",
      "This is helpful!",
      "Great insights!"
    ]
  }
}
```

## Bulk Messaging Recipients (data/recipients_template.json)

Configure bulk message campaigns (use sparingly!).

### Format

```json
[
  {
    "name": "Person's Name",
    "profile_url": "https://www.linkedin.com/in/username/",
    "message": "Personalized message text"
  }
]
```

### Tips

- Keep messages personalized and professional
- Don't spam - LinkedIn will detect this
- Use only for genuine networking
- Add significant delays between messages (10-15 seconds minimum)

### Example

```json
[
  {
    "name": "Alex Johnson",
    "profile_url": "https://www.linkedin.com/in/alexjohnson/",
    "message": "Hi Alex, I noticed we both work in Python development. I'd love to connect and share insights!"
  },
  {
    "name": "Sarah Williams",
    "profile_url": "https://www.linkedin.com/in/sarahwilliams/",
    "message": "Hi Sarah, your recent post about automation was fascinating. Would love to connect!"
  }
]
```

## Scheduler Configuration (scheduler.py)

To modify the schedule, edit `scheduler.py`:

### Current Schedule

```python
# Check for scheduled posts every 30 minutes
schedule.every(30).minutes.do(scheduled_posting)

# Engage with feed twice a day
schedule.every().day.at("09:00").do(scheduled_engagement)
schedule.every().day.at("17:00").do(scheduled_engagement)

# Reply to comments three times a day
schedule.every().day.at("10:00").do(scheduled_reply)
schedule.every().day.at("14:00").do(scheduled_reply)
schedule.every().day.at("18:00").do(scheduled_reply)

# Check messages every 2 hours
schedule.every(2).hours.do(scheduled_message_check)
```

### Customization Examples

```python
# Run every hour
schedule.every().hour.do(your_function)

# Run every day at specific time
schedule.every().day.at("10:30").do(your_function)

# Run every Monday
schedule.every().monday.do(your_function)

# Run every 10 minutes
schedule.every(10).minutes.do(your_function)
```

## Best Practices

1. **Start Conservative**: Begin with low engagement numbers and increase gradually
2. **Monitor Activity**: Check your LinkedIn account regularly for warnings
3. **Realistic Delays**: Use 2-5 second delays minimum to appear human
4. **Quality Over Quantity**: Better to post less but with quality content
5. **Personalization**: Customize templates to match your voice
6. **Test Account**: Always test on a non-primary account first
7. **Regular Updates**: LinkedIn changes UI frequently, be prepared to update selectors

## Troubleshooting

### Bot is too slow
- Decrease `MAX_DELAY` in `.env`
- Reduce `SCROLL_DELAY`

### Bot is being detected
- Increase `MIN_DELAY` and `MAX_DELAY`
- Reduce engagement numbers
- Add more variety to comments/replies

### Posts aren't being published
- Check `schedule_time` format is correct
- Ensure time is in the future
- Verify `posted: false` in the JSON file

---

Need more help? Check the main [README.md](README.md) or [QUICK_START.md](QUICK_START.md).

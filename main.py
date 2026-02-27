#!/usr/bin/env python3
"""
LinkedIn Automation Bot - Main Entry Point
For educational and testing purposes only
"""

from linkedin_bot import LinkedInBot
from dotenv import load_dotenv
import os
import utils
import sys

# Load environment variables
load_dotenv()

def print_menu():
    """Print main menu"""
    print("\n" + "="*60)
    print("LinkedIn Automation Bot - AI-Powered Edition")
    print("="*60)
    print("\n=== AI-Powered Features (NEW) ===")
    print("1.  Generate and post AI content")
    print("2.  Intelligent feed engagement (AI-filtered)")
    print("3.  View analytics dashboard")
    print("\n=== Scheduled Content ===")
    print("14. Schedule AI content (with optional video)")
    print("15. Preview scheduled content")
    print("16. Post due scheduled content now")
    print("\n=== Original Features ===")
    print("4.  Create a single post (manual)")
    print("5.  Check and post scheduled posts")
    print("6.  Engage with feed (legacy random)")
    print("7.  Search and engage with keyword")
    print("8.  Reply to comments")
    print("9.  Send a message")
    print("10. Send connection request")
    print("11. Check messages")
    print("\n=== Automated Campaigns ===")
    print("12. Run intelligent growth campaign (AI)")
    print("13. Run all automated tasks (legacy)")
    print("17. Full autopilot (post + engage + connect)")
    print("\n0.  Exit")
    print("="*60)

def create_single_post(bot):
    """Interactive post creation"""
    content = input("Enter post content: ")
    media = input("Enter media path (or press Enter to skip): ").strip()

    if bot.create_post(content, media if media else None):
        print("Post created successfully!")
    else:
        print("Failed to create post")

def engage_with_feed(bot):
    """Interactive feed engagement"""
    max_engagements = input("Max engagements (default 10): ").strip()
    max_engagements = int(max_engagements) if max_engagements else 10

    count = bot.engage_with_feed(max_engagements)
    print(f"Engaged with {count} posts")

def search_and_engage(bot):
    """Interactive search and engage"""
    keyword = input("Enter keyword to search: ")
    max_engagements = input("Max engagements (default 5): ").strip()
    max_engagements = int(max_engagements) if max_engagements else 5

    count = bot.search_and_engage(keyword, max_engagements)
    print(f"Engaged with {count} posts")

def send_message(bot):
    """Interactive message sending"""
    recipient_url = input("Enter recipient profile URL: ")
    message = input("Enter message: ")

    if bot.send_message(recipient_url, message):
        print("Message sent successfully!")
    else:
        print("Failed to send message")

def send_connection_request(bot):
    """Interactive connection request"""
    recipient_url = input("Enter recipient profile URL: ")
    message = input("Enter message (optional): ").strip()

    if bot.send_connection_request(recipient_url, message or "I'd like to connect with you!"):
        print("Connection request sent!")
    else:
        print("Failed to send connection request")

def run_all_tasks(bot):
    """Run all automated tasks once"""
    print("\n=== Running all automated tasks ===\n")

    # Check scheduled posts
    print("1. Checking scheduled posts...")
    bot.check_scheduled_posts('data/posts_template.json')
    utils.random_delay(3, 5)

    # Engage with feed
    print("\n2. Engaging with feed...")
    bot.engage_with_feed(max_engagements=5)
    utils.random_delay(5, 10)

    # Reply to comments
    print("\n3. Replying to comments...")
    bot.reply_to_comments(max_replies=3)
    utils.random_delay(5, 10)

    # Check messages
    print("\n4. Checking messages...")
    bot.check_messages(auto_respond=True, response_template="Thanks for your message!")
    utils.random_delay(3, 5)

    print("\n=== All tasks completed ===")

def main():
    """Main function"""
    print("\n" + "="*50)
    print("LinkedIn Automation Bot")
    print("For Educational Purposes Only")
    print("="*50)

    # Get credentials
    email = os.getenv('LINKEDIN_EMAIL')
    password = os.getenv('LINKEDIN_PASSWORD')
    headless = os.getenv('HEADLESS', 'False').lower() == 'true'

    if not email or not password:
        print("\nError: Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file")
        print("Copy .env.example to .env and fill in your credentials")
        sys.exit(1)

    # Initialize bot
    print("\nInitializing bot...")
    bot = LinkedInBot(email, password, headless=headless)

    if not bot.start():
        print("Failed to login. Please check your credentials.")
        sys.exit(1)

    # Load configurations
    bot.load_reply_templates('data/reply_templates.json')
    bot.load_engagement_config('data/engagement_config.json')

    # Main loop
    while True:
        try:
            print_menu()
            choice = input("\nEnter your choice: ").strip()

            # AI-Powered Features
            if choice == '1':
                theme = input("Enter theme (or press Enter for auto): ").strip()
                theme = theme if theme else None
                if bot.generate_and_post_content(theme=theme):
                    print("✓ AI-generated post published successfully!")
                else:
                    print("✗ Failed to generate/post content")

            elif choice == '2':
                max_posts = input("Max posts to engage with (default 10): ").strip()
                max_posts = int(max_posts) if max_posts else 10
                count = bot.intelligent_feed_engagement(max_posts=max_posts)
                print(f"✓ Engaged with {count} relevant posts using AI filtering")

            elif choice == '3':
                bot.view_analytics()

            # Original Features
            elif choice == '4':
                create_single_post(bot)
            elif choice == '5':
                count = bot.check_scheduled_posts('data/posts_template.json')
                print(f"Posted {count} scheduled posts")
            elif choice == '6':
                engage_with_feed(bot)
            elif choice == '7':
                search_and_engage(bot)
            elif choice == '8':
                count = bot.reply_to_comments(max_replies=5)
                print(f"Replied to {count} comments")
            elif choice == '9':
                send_message(bot)
            elif choice == '10':
                send_connection_request(bot)
            elif choice == '11':
                auto_respond = input("Auto-respond to messages? (y/n): ").lower() == 'y'
                count = bot.check_messages(
                    auto_respond=auto_respond,
                    response_template="Thanks for your message!"
                )
                print(f"Found {count} unread messages")

            # Automated Campaigns
            elif choice == '12':
                print("\n" + "="*60)
                print("Running Intelligent Growth Campaign (AI-Powered)")
                print("="*60)

                print("\n[1/4] Generating and posting AI content...")
                bot.generate_and_post_content()
                utils.random_delay(3, 5)

                print("\n[2/4] Intelligent feed engagement...")
                bot.intelligent_feed_engagement(max_posts=10)
                utils.random_delay(5, 10)

                print("\n[3/4] Replying to comments...")
                bot.reply_to_comments(max_replies=3)
                utils.random_delay(5, 10)

                print("\n[4/4] Viewing analytics...")
                bot.view_analytics()

                print("\n✓ Campaign complete!")
                print("="*60)

            elif choice == '13':
                run_all_tasks(bot)

            elif choice == '14':
                print("\n=== Schedule AI Content ===")
                days_input = input("How many days to schedule? (default 7): ").strip()
                days = int(days_input) if days_input else 7

                video_folder = input("Video folder path (or Enter to skip): ").strip()
                video_folder = video_folder if video_folder else None

                items = bot.schedule_video_content(days=days, video_folder=video_folder)
                if items:
                    print(f"\n✓ Scheduled {len(items)} posts!")
                    for item in items:
                        media_tag = f" + video" if item.get('media') else ""
                        print(f"  [{item['id']}] {item['schedule_time']} | {item['theme'][:40]}{media_tag}")
                    print(f"\nPosts saved to data/scheduled_content.json")
                    print("They will auto-post at the scheduled times when the scheduler is running.")
                else:
                    print("✗ Failed to schedule content")

            elif choice == '15':
                pending = bot.preview_scheduled_content()
                if not pending:
                    print("No pending scheduled content.")

            elif choice == '16':
                count = bot.check_ai_scheduled_posts()
                print(f"✓ Posted {count} due scheduled post(s)")

            elif choice == '17':
                print("\n" + "="*60)
                print("Full Autopilot Mode (Post + Engage + Connect)")
                print("="*60)

                engage_input = input("Max posts to engage with (default 10): ").strip()
                max_engage = int(engage_input) if engage_input else 10

                connect_input = input("Max connection requests (default 5): ").strip()
                max_connect = int(connect_input) if connect_input else 5

                results = bot.run_full_autopilot(
                    max_posts_to_engage=max_engage,
                    max_connections=max_connect
                )

            elif choice == '0':
                print("\nExiting...")
                bot.stop()
                break

            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            bot.stop()
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            utils.log(f"Error in main loop: {str(e)}", "ERROR")

if __name__ == "__main__":
    # Support --autopilot CLI flag to skip menu
    if '--autopilot' in sys.argv:
        print("\n" + "="*50)
        print("LinkedIn Automation Bot - Autopilot Mode")
        print("For Educational Purposes Only")
        print("="*50)

        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')
        headless = os.getenv('HEADLESS', 'False').lower() == 'true'

        if not email or not password:
            print("\nError: Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file")
            sys.exit(1)

        bot = LinkedInBot(email, password, headless=headless)
        if not bot.start():
            print("Failed to login.")
            sys.exit(1)

        bot.load_reply_templates('data/reply_templates.json')
        bot.load_engagement_config('data/engagement_config.json')

        try:
            bot.run_full_autopilot(max_posts_to_engage=10, max_connections=5)
        except KeyboardInterrupt:
            print("\nInterrupted.")
        finally:
            bot.stop()
    else:
        main()

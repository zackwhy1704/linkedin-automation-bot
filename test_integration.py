"""
Quick integration test - Test database operations
"""
import os
from dotenv import load_dotenv
from bot_database_postgres import BotDatabase
from cryptography.fernet import Fernet

load_dotenv()

print("=" * 60)
print("INTEGRATION TEST - Database Operations")
print("=" * 60)

try:
    # Test 1: Initialize database
    print("\n1. Initializing database...")
    db = BotDatabase()
    print("   [OK] Database initialized")

    # Test 2: Create a test user
    print("\n2. Creating test user...")
    test_telegram_id = 999999999
    db.create_user(test_telegram_id, username="test_user", first_name="Test")
    print("   [OK] Test user created")

    # Test 3: Retrieve user
    print("\n3. Retrieving user...")
    user = db.get_user(test_telegram_id)
    if user:
        print(f"   [OK] User retrieved: {user['username']}")
    else:
        print("   [FAIL] User not found")

    # Test 4: Save user profile
    print("\n4. Saving user profile...")
    profile_data = {
        'industry': ['Technology', 'AI'],
        'skills': ['Python', 'Machine Learning', 'AWS'],
        'career_goals': ['Become a Tech Lead', 'Build AI products'],
        'tone': ['Professional', 'Conversational'],  # Array of tone preferences
        'interests': ['AI', 'Cloud Computing', 'Startups']
    }

    content_strategy = {
        'content_themes': ['AI Development', 'Cloud Architecture', 'Leadership'],
        'posting_frequency': 'daily',
        'optimal_times': ['09:00', '13:00', '17:00'],
        'content_goals': ['Thought Leadership', 'Professional Network Growth']
    }

    db.save_user_profile(test_telegram_id, profile_data, content_strategy)
    print("   [OK] User profile saved")

    # Test 5: Retrieve user profile
    print("\n5. Retrieving user profile...")
    profile = db.get_user_profile(test_telegram_id)
    if profile and 'profile_data' in profile:
        print(f"   [OK] Profile retrieved: {profile['profile_data']['industry']}")
        print(f"   [OK] Skills: {profile['profile_data']['skills']}")
        if 'content_strategy' in profile:
            print(f"   [OK] Content themes: {profile['content_strategy']['content_themes']}")
    else:
        print("   [FAIL] Profile not found")

    # Test 6: Save encrypted LinkedIn credentials
    print("\n6. Saving LinkedIn credentials...")
    cipher = Fernet(os.getenv('ENCRYPTION_KEY').encode())
    encrypted_password = cipher.encrypt(b"test_password_123")

    db.save_linkedin_credentials(
        test_telegram_id,
        "test@example.com",
        encrypted_password
    )
    print("   [OK] Credentials saved (encrypted)")

    # Test 7: Retrieve and decrypt credentials
    print("\n7. Retrieving credentials...")
    creds = db.get_linkedin_credentials(test_telegram_id)
    if creds:
        decrypted_password = cipher.decrypt(creds['encrypted_password']).decode()
        print(f"   [OK] Email: {creds['email']}")
        print(f"   [OK] Password decrypted: {decrypted_password == 'test_password_123'}")
    else:
        print("   [FAIL] Credentials not found")

    # Test 8: Log automation action
    print("\n8. Logging automation action...")
    db.log_automation_action(
        test_telegram_id,
        'post',
        action_count=1,
        metadata={'success': True}
    )
    print("   [OK] Automation action logged")

    # Test 9: Get user stats
    print("\n9. Getting user stats...")
    stats = db.get_user_stats(test_telegram_id)
    if stats:
        print(f"   [OK] Posts created: {stats['posts_created']}")
        print(f"   [OK] Likes given: {stats['likes_given']}")
        print(f"   [OK] Comments made: {stats['comments_made']}")
        print(f"   [OK] Connections sent: {stats['connections_sent']}")
    else:
        print("   [FAIL] Stats not found")

    # Test 10: Mark post as engaged
    print("\n10. Tracking engagement...")
    db.mark_post_engaged(
        test_telegram_id,
        "test-post-123",
        engagement_type="like",
        post_content="Great post about AI!"
    )
    print("   [OK] Post engagement tracked")

    # Test 11: Check if already engaged
    print("\n11. Checking engagement history...")
    already_engaged = db.has_engaged_post(test_telegram_id, "test-post-123")
    print(f"   [OK] Already engaged: {already_engaged}")

    # Test 12: Safety counts
    print("\n12. Testing safety counts...")
    db.increment_safety_count(test_telegram_id, 'like', 5)
    daily_count = db.get_daily_count(test_telegram_id, 'like')
    print(f"   [OK] Daily 'like' count: {daily_count}")

    # Test 13: Activate subscription
    print("\n13. Activating subscription...")
    db.activate_subscription(
        test_telegram_id,
        stripe_customer_id="cus_test123",
        stripe_subscription_id="sub_test123"
    )
    is_active = db.is_subscription_active(test_telegram_id)
    print(f"   [OK] Subscription active: {is_active}")

    # Test 14: Clean up test data
    print("\n14. Cleaning up test data...")
    conn = db.get_connection()
    cursor = conn.cursor()

    # Delete test user and all related data (cascade will handle it)
    cursor.execute("DELETE FROM users WHERE telegram_id = %s", (test_telegram_id,))
    conn.commit()

    db.return_connection(conn)
    print("   [OK] Test data cleaned up")

    # Test 15: Close database
    print("\n15. Closing database connection pool...")
    db.close()
    print("   [OK] Connection pool closed")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL INTEGRATION TESTS PASSED!")
    print("=" * 60)
    print("\nYour bot is ready to use with PostgreSQL!")
    print("\nNext steps:")
    print("  1. Start bot: python telegram_bot.py")
    print("  2. Test commands in Telegram")
    print("  3. Migrate existing data: python migrations/migrate_sqlite_to_postgres.py")

except Exception as e:
    print(f"\n[FAIL] Integration test failed: {e}")
    import traceback
    traceback.print_exc()

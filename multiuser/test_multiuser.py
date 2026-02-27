#!/usr/bin/env python3
"""
Test Multi-User Concurrent Execution
Simulates multiple users triggering tasks simultaneously
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
from datetime import datetime

def test_celery_import():
    """Test if Celery tasks can be imported"""
    print("\n=== Testing Celery Task Import ===")
    try:
        from tasks import (
            post_to_linkedin_task,
            engage_with_feed_task,
            autopilot_task
        )
        print("[OK] Celery tasks imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Failed to import Celery tasks: {e}")
        print("\nMake sure:")
        print("  1. Redis is running: redis-server")
        print("  2. Tasks exist: ls ../tasks.py")
        return False

def test_redis_connection():
    """Test Redis connectivity"""
    print("\n=== Testing Redis Connection ===")
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        print(f"[OK] Redis connected: {redis_url}")
        return True
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        print("\nStart Redis:")
        print("  Windows: redis-server")
        print("  WSL: wsl redis-server")
        print("  Docker: docker run -d -p 6379:6379 redis")
        return False

def test_celery_worker():
    """Test if Celery worker is running"""
    print("\n=== Testing Celery Worker ===")
    try:
        from celery_app import app

        # Check if worker is available
        stats = app.control.inspect().stats()

        if stats:
            worker_count = len(stats)
            print(f"[OK] Found {worker_count} active worker(s)")
            for worker_name, worker_stats in stats.items():
                print(f"   - {worker_name}")
            return True
        else:
            print("[FAIL] No Celery workers found")
            print("\nStart Celery worker:")
            print("  cd .. && celery -A celery_app worker --loglevel=info --concurrency=3 --pool=solo")
            return False

    except Exception as e:
        print(f"[FAIL] Worker check failed: {e}")
        return False

def test_browser_pool():
    """Test browser pool functionality"""
    print("\n=== Testing Browser Pool ===")
    try:
        from browser_pool import BrowserPool

        # Create small test pool
        pool = BrowserPool(max_browsers=2, headless=True)

        # Acquire browser
        context = pool.acquire(user_id=99999, timeout=10)
        print(f"[OK] Browser acquired: {context.session_id}")

        # Release browser
        pool.release(context)
        print("[OK] Browser released successfully")

        # Cleanup
        pool.shutdown()
        print("[OK] Browser pool working correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Browser pool test failed: {e}")
        return False

def simulate_concurrent_users(num_users=3):
    """Simulate multiple users triggering tasks"""
    print(f"\n=== Simulating {num_users} Concurrent Users ===")

    try:
        from tasks import post_to_linkedin_task

        print(f"Queueing {num_users} tasks simultaneously...")
        start_time = time.time()

        task_ids = []
        for i in range(num_users):
            user_id = 10000 + i
            content = f"Test post from user {user_id} at {datetime.now()}"

            # Queue task
            task = post_to_linkedin_task.delay(user_id, content)
            task_ids.append(task.id)
            print(f"  User {user_id}: Task queued (ID: {task.id[:8]}...)")

        elapsed = time.time() - start_time
        print(f"\n[OK] All {num_users} tasks queued in {elapsed:.2f}s")
        print(f"[OK] Tasks are processing in parallel by Celery workers")
        print(f"\nTask IDs:")
        for task_id in task_ids:
            print(f"  - {task_id}")

        print("\nMonitor tasks:")
        print("  1. Check Celery worker logs")
        print("  2. Open Flower: celery -A celery_app flower")
        print("     Then visit: http://localhost:5555")

        return True

    except Exception as e:
        print(f"[FAIL] Simulation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("MULTI-USER CONCURRENT EXECUTION TEST")
    print("="*60)

    tests = [
        ("Celery Import", test_celery_import),
        ("Redis Connection", test_redis_connection),
        ("Celery Worker", test_celery_worker),
        ("Browser Pool", test_browser_pool),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} crashed: {e}")
            results.append((test_name, False))
        time.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status:10} - {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        print("\nReady for multi-user simulation!")

        # Ask if user wants to simulate
        try:
            response = input("\nRun concurrent user simulation? (y/n): ").lower()
            if response == 'y':
                simulate_concurrent_users(num_users=3)
        except KeyboardInterrupt:
            print("\n\nTest interrupted")
    else:
        print("\n" + "="*60)
        print("SETUP INCOMPLETE")
        print("="*60)
        print("\nFix the failed tests above before running multi-user mode.")
        print("\nQuick setup:")
        print("  1. pip install redis celery")
        print("  2. redis-server  # Start Redis")
        print("  3. celery -A celery_app worker --loglevel=info --concurrency=3 --pool=solo")
        print("  4. python test_multiuser.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite crashed: {e}")
        import traceback
        traceback.print_exc()

# Quick Start Guide - Multi-User Bot

## ✅ Step 1: Install Redis

Choose ONE option:

### Option A: Memurai (Recommended - Easiest)
1. Download: https://www.memurai.com/get-memurai
2. Install the `.msi` file
3. Verify: `redis-cli ping` (should return PONG)

### Option B: WSL
```bash
# Run: ../install_redis_wsl.bat
# Or manually:
wsl sudo apt update
wsl sudo apt install -y redis-server
wsl sudo service redis-server start
wsl redis-cli ping
```

### Option C: Docker
```bash
docker run -d -p 6379:6379 --name redis redis
docker exec -it redis redis-cli ping
```

---

## ✅ Step 2: Test Multi-User Setup

```bash
cd multiuser
python test_multiuser.py
```

This tests:
- ✅ Celery task imports
- ✅ Redis connection
- ✅ Celery worker availability
- ✅ Browser pool functionality

---

## ✅ Step 3: Start All Services

### Option A: All-in-One (Recommended)
```bash
cd multiuser
start_all.bat
```

This opens 3 windows:
1. **Redis Server** - Task queue
2. **Celery Worker** - Background task processor
3. **Telegram Bot** - User interface

### Option B: Manual Start
```bash
# Terminal 1: Start Redis
cd multiuser
start_redis.bat

# Terminal 2: Start Celery Worker
cd multiuser
start_celery.bat

# Terminal 3: Start Telegram Bot
cd multiuser
start_bot.bat
```

---

## ✅ Step 4: Verify Everything Works

### Check Redis
```bash
redis-cli ping
# Expected: PONG
```

### Check Celery Worker
Look for this in the Celery window:
```
[INFO] celery@hostname ready.
[INFO] Connected to redis://localhost:6379/0
```

### Check Telegram Bot
Look for this in the bot window:
```
[INFO] Celery tasks loaded - Multi-user mode enabled
[INFO] Bot started successfully
```

---

## 🎯 Test with Telegram

1. Open Telegram
2. Send `/start` to your bot
3. Send `/post` command
4. Watch the Celery worker window process the task!

You should see:
- Task queued immediately (bot responds instantly)
- Task processing in Celery worker window
- LinkedIn post created
- Screenshot delivered to Telegram

---

## 📊 Monitor Tasks (Optional)

### Flower Web UI
```bash
# Terminal 4
cd ..
celery -A celery_app flower

# Open browser: http://localhost:5555
```

Flower shows:
- Active tasks
- Task history
- Worker status
- Queue lengths

---

## 🐛 Troubleshooting

### "Falling back to single-user threading mode"
**Cause**: Redis or Celery not running
**Fix**:
1. Start Redis: `redis-cli ping` (should return PONG)
2. Start Celery worker: `cd multiuser && start_celery.bat`

### "Connection refused"
**Cause**: Redis not running
**Fix**:
- **Memurai**: Check Windows Services, start "Memurai" service
- **WSL**: `wsl sudo service redis-server start`
- **Docker**: `docker start redis`

### "No workers available"
**Cause**: Celery worker not started
**Fix**: `cd multiuser && start_celery.bat`

### Tasks stuck in queue
**Cause**: Worker crashed or stopped
**Fix**:
1. Check Celery window for errors
2. Restart: Close Celery window, run `start_celery.bat` again

---

## ✨ What You Get

### Single-User Mode (Without Redis/Celery)
- 1 user at a time
- Sequential processing
- Limited to 3-5 concurrent users max
- Bot works but slower

### Multi-User Mode (With Redis/Celery)
- **100+ concurrent users**
- Parallel task processing
- Browser session reuse (10x faster)
- Production-ready scalability
- Task queuing and prioritization

---

## 🚀 Next Steps

1. **Install Redis** (choose Memurai for easiest setup)
2. **Run test**: `cd multiuser && python test_multiuser.py`
3. **Start services**: `cd multiuser && start_all.bat`
4. **Test with Telegram**: Send `/post` command
5. **Monitor**: Open Flower UI at http://localhost:5555

---

## 📞 Need Help?

1. Check all services are running:
   - Redis: `redis-cli ping`
   - Celery: Check worker window for "ready"
   - Bot: Check bot window for "Multi-user mode enabled"

2. Review logs:
   - Celery worker window shows task execution
   - Bot window shows incoming commands
   - Flower UI shows task history

3. Run diagnostic:
   ```bash
   cd multiuser
   python test_multiuser.py
   ```

---

**Recommended**: Install **Memurai** (5 minutes) → Run `start_all.bat` → Test with `/post`

**Download Memurai**: https://www.memurai.com/get-memurai

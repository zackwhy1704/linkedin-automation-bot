# Redis Installation Guide for Windows

## 🎯 Quick Install (Choose One)

### ✅ Option 1: Memurai (Easiest - Recommended)

**Memurai** is a Redis-compatible server made specifically for Windows.

1. **Download**: https://www.memurai.com/get-memurai
2. **Choose**: "Memurai Developer Edition" (FREE)
3. **Install**: Double-click the downloaded `.msi` file
4. **Verify**:
   ```bash
   redis-server --version
   redis-cli ping
   # Should return: PONG
   ```

**Pros**: Native Windows, runs as service, GUI included
**Cons**: None

---

### ✅ Option 2: Docker (If you have Docker)

```bash
# Pull and run Redis
docker run -d -p 6379:6379 --name redis redis

# Test
docker exec -it redis redis-cli ping
# Should return: PONG

# View logs
docker logs redis

# Stop
docker stop redis

# Start again
docker start redis
```

**Pros**: Clean, isolated, easy to remove
**Cons**: Requires Docker Desktop

---

### ✅ Option 3: WSL (Windows Subsystem for Linux)

```bash
# Install WSL (if not installed)
wsl --install

# Restart computer (if first time)

# Install Redis in WSL
wsl sudo apt update
wsl sudo apt install redis-server -y

# Start Redis
wsl redis-server &

# Test
wsl redis-cli ping
# Should return: PONG
```

**Pros**: True Redis, latest version
**Cons**: Requires WSL setup

---

### ⚠️ Option 4: Microsoft Archive (Old Version)

**Not recommended** - this is an old version (3.0.504) from 2016.

1. Download: https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi
2. Install
3. Add to PATH: `C:\Program Files\Redis`

---

## 🚀 Quick Start After Installation

### 1. Start Redis Server
```bash
# If using Memurai or Microsoft Archive:
redis-server

# If using Docker:
docker start redis

# If using WSL:
wsl redis-server &
```

### 2. Test Connection
```bash
redis-cli ping
# Should return: PONG
```

### 3. Run Multi-User Bot
```bash
cd multiuser
start_all.bat
```

---

## 🧪 Verify Installation

Run this test:

```bash
# Test 1: Check if Redis command is available
where redis-server

# Test 2: Start Redis
redis-server

# Test 3: In another terminal, test connection
redis-cli ping

# Test 4: Set and get a value
redis-cli SET test "Hello"
redis-cli GET test
# Should return: "Hello"
```

---

## 🔧 Troubleshooting

### "redis-server is not recognized"

**Cause**: Redis not in PATH
**Fix**:

**For Memurai:**
```bash
# Add to PATH
set PATH=%PATH%;C:\Program Files\Memurai
```

**For WSL:**
```bash
# Always use with wsl prefix
wsl redis-server
```

**For Docker:**
```bash
# Use docker command
docker start redis
```

---

### Redis starts but won't stay running

**Cause**: Port 6379 already in use
**Fix**:

```bash
# Find what's using port 6379
netstat -ano | findstr :6379

# Kill the process
taskkill /PID <process_id> /F

# Or use different port
redis-server --port 6380
```

Then update `.env`:
```env
REDIS_URL=redis://localhost:6380/0
```

---

### "Connection refused" when testing

**Cause**: Redis not running
**Fix**:

```bash
# Start Redis server first
redis-server

# In another terminal, test
redis-cli ping
```

---

### Redis closes when I close the terminal

**Cause**: Running in foreground
**Fix**:

**Option A**: Keep terminal open

**Option B**: Install as Windows Service (Memurai does this automatically)

**Option C**: Use Docker
```bash
docker run -d -p 6379:6379 --name redis redis
```

**Option D**: Use WSL in background
```bash
wsl sudo service redis-server start
```

---

## 📋 Configuration for Multi-User Bot

### Update .env file

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# If using WSL and Redis isn't responding:
# Try: redis://127.0.0.1:6379/0

# If using different port:
# REDIS_URL=redis://localhost:6380/0

# Browser Pool
BROWSER_POOL_SIZE=5
CELERY_WORKER_CONCURRENCY=3
```

---

## ✅ Recommended Setup

**For Development (Local Machine):**
- Use **Memurai** (easiest, most reliable)
- Or **Docker** (if you already have it)

**For Production (Server):**
- Use **Docker** (isolated, manageable)
- Or **AWS ElastiCache** (managed service)

---

## 🎯 Next Steps After Redis Installation

1. **Verify Redis is running**:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Test multi-user bot**:
   ```bash
   cd multiuser
   python test_multiuser.py
   ```

3. **Start all services**:
   ```bash
   cd multiuser
   start_all.bat
   ```

---

## 📞 Still Having Issues?

### Check Redis Status
```bash
# Windows
tasklist | findstr redis

# WSL
wsl ps aux | grep redis

# Docker
docker ps | grep redis
```

### View Redis Logs
```bash
# If running in terminal: logs show in terminal

# If running as service (Memurai):
# Check: C:\Program Files\Memurai\logs\

# Docker:
docker logs redis

# WSL:
wsl sudo tail -f /var/log/redis/redis-server.log
```

### Restart Redis
```bash
# Windows service (Memurai):
net stop memurai
net start memurai

# Docker:
docker restart redis

# WSL:
wsl sudo service redis-server restart
```

---

## 🌟 Quick Comparison

| Method | Difficulty | Speed | Recommended For |
|--------|------------|-------|-----------------|
| **Memurai** | ⭐ Easy | Fast | Everyone |
| **Docker** | ⭐⭐ Medium | Fast | Docker users |
| **WSL** | ⭐⭐⭐ Hard | Medium | Linux familiarity |
| **MS Archive** | ⭐⭐ Medium | Fast | Legacy only |

---

**Recommended**: Install **Memurai** → It just works! ✨

**Download**: https://www.memurai.com/get-memurai

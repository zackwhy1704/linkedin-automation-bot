#!/bin/bash
# =============================================================================
# LinkedIn Bot - Deploy / Update Script
# Run this whenever you push new code to GitHub
# Usage: bash deployment/3_deploy.sh
# =============================================================================
set -e

APP_PATH="/home/linkedin/linkedin-automation-bot"

echo ""
echo "=============================================="
echo "  LinkedIn Bot - Deploying Update"
echo "=============================================="
echo ""

cd "$APP_PATH"

# --- Pull latest code ---
echo "[1/4] Pulling latest code from GitHub..."
sudo -u linkedin git pull
echo "  Done."

# --- Install any new dependencies ---
echo ""
echo "[2/4] Installing/updating Python dependencies..."
sudo -u linkedin bash -c "source $APP_PATH/venv/bin/activate && pip install -r requirements.txt -q"
echo "  Done."

# --- Reload systemd (in case service files changed) ---
echo ""
echo "[3/4] Reloading systemd daemon..."
cp "$APP_PATH/deployment/systemd/telegram-bot.service"   /etc/systemd/system/
cp "$APP_PATH/deployment/systemd/celery-worker.service"  /etc/systemd/system/
cp "$APP_PATH/deployment/systemd/payment-server.service" /etc/systemd/system/
systemctl daemon-reload
echo "  Done."

# --- Restart services ---
echo ""
echo "[4/4] Restarting services..."

systemctl restart payment-server
sleep 2
echo "  payment-server restarted."

systemctl restart celery-worker
sleep 3
echo "  celery-worker restarted."

systemctl restart telegram-bot
sleep 2
echo "  telegram-bot restarted."

# --- Final status ---
echo ""
echo "=============================================="
echo "  Deployment Complete - Service Status"
echo "=============================================="
echo ""

for SERVICE in payment-server celery-worker telegram-bot; do
    STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "failed")
    if [ "$STATUS" = "active" ]; then
        echo "  [OK] $SERVICE"
    else
        echo "  [FAIL] $SERVICE — check: journalctl -u $SERVICE -n 20"
    fi
done

echo ""

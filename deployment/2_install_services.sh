#!/bin/bash
# =============================================================================
# LinkedIn Bot - Install Systemd Services
# Run this after 1_setup_server.sh and after uploading .env
# Usage: bash deployment/2_install_services.sh
# =============================================================================
set -e

APP_PATH="/home/linkedin/linkedin-automation-bot"
SYSTEMD_DIR="/etc/systemd/system"

echo ""
echo "=============================================="
echo "  Installing Systemd Services"
echo "=============================================="

# --- Verify .env exists ---
if [ ! -f "$APP_PATH/.env" ]; then
    echo ""
    echo "ERROR: $APP_PATH/.env not found!"
    echo "Upload it first:"
    echo "  scp .env root@YOUR_SERVER_IP:$APP_PATH/.env"
    echo "  chown linkedin:linkedin $APP_PATH/.env"
    echo "  chmod 600 $APP_PATH/.env"
    exit 1
fi

# Fix .env permissions
chown linkedin:linkedin "$APP_PATH/.env"
chmod 600 "$APP_PATH/.env"
echo "  .env permissions set."

# --- Install service files ---
echo ""
echo "Installing service files..."
cp "$APP_PATH/deployment/systemd/telegram-bot.service"  "$SYSTEMD_DIR/"
cp "$APP_PATH/deployment/systemd/celery-worker.service" "$SYSTEMD_DIR/"
cp "$APP_PATH/deployment/systemd/payment-server.service" "$SYSTEMD_DIR/"

systemctl daemon-reload
echo "  Service files installed and daemon reloaded."

# --- Enable services (auto-start on reboot) ---
echo ""
echo "Enabling services for auto-start..."
systemctl enable telegram-bot
systemctl enable celery-worker
systemctl enable payment-server

# --- Start services ---
echo ""
echo "Starting services..."

echo "  Starting payment-server..."
systemctl start payment-server
sleep 2

echo "  Starting celery-worker..."
systemctl start celery-worker
sleep 3

echo "  Starting telegram-bot..."
systemctl start telegram-bot
sleep 2

# --- Status check ---
echo ""
echo "=============================================="
echo "  Service Status"
echo "=============================================="
echo ""

for SERVICE in payment-server celery-worker telegram-bot; do
    STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "failed")
    if [ "$STATUS" = "active" ]; then
        echo "  [OK] $SERVICE is running"
    else
        echo "  [FAIL] $SERVICE is NOT running (status: $STATUS)"
        echo "         Check logs: journalctl -u $SERVICE -n 30"
    fi
done

echo ""
echo "=============================================="
echo "  Useful Commands"
echo "=============================================="
echo ""
echo "  View live logs:"
echo "    tail -f $APP_PATH/logs/telegram-bot.log"
echo "    tail -f $APP_PATH/logs/celery-worker.log"
echo "    tail -f $APP_PATH/logs/payment-server.log"
echo ""
echo "  Restart a service:"
echo "    systemctl restart telegram-bot"
echo "    systemctl restart celery-worker"
echo "    systemctl restart payment-server"
echo ""
echo "  Stop all:"
echo "    systemctl stop telegram-bot celery-worker payment-server"
echo ""
echo "  Service status:"
echo "    systemctl status telegram-bot"
echo ""

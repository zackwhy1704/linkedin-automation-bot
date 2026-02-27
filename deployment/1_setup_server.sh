#!/bin/bash
# =============================================================================
# LinkedIn Bot - Server Setup Script
# Run this ONCE on a fresh Hetzner Ubuntu 22.04 server
# Usage: bash 1_setup_server.sh
# =============================================================================
set -e  # Exit on any error

echo ""
echo "=============================================="
echo "  LinkedIn Bot - Server Setup"
echo "  Ubuntu 22.04 | Hetzner CX32"
echo "=============================================="
echo ""

# --- Prompt for config ---
read -p "Enter your GitHub repo URL (e.g. https://github.com/you/linkedin-automation-bot.git): " REPO_URL
read -p "Enter the server's public IP address: " SERVER_IP
read -p "App directory name [linkedin-automation-bot]: " APP_DIR
APP_DIR=${APP_DIR:-linkedin-automation-bot}

APP_PATH="/home/linkedin/$APP_DIR"

echo ""
echo "[1/9] Updating system packages..."
apt-get update -y
apt-get upgrade -y
apt-get install -y curl wget git unzip software-properties-common ufw nginx

# --- Create dedicated user ---
echo ""
echo "[2/9] Creating 'linkedin' system user..."
if id "linkedin" &>/dev/null; then
    echo "  User 'linkedin' already exists, skipping."
else
    useradd -m -s /bin/bash linkedin
    echo "  User 'linkedin' created."
fi

# --- Python 3.11 ---
echo ""
echo "[3/9] Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# --- Google Chrome ---
echo ""
echo "[4/9] Installing Google Chrome (stable)..."
wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y /tmp/chrome.deb || apt-get install -f -y
rm /tmp/chrome.deb
echo "  Chrome version: $(google-chrome --version)"

# --- Redis ---
echo ""
echo "[5/9] Installing Redis..."
apt-get install -y redis-server
# Bind to localhost only (security)
sed -i 's/^bind .*/bind 127.0.0.1/' /etc/redis/redis.conf
systemctl enable redis-server
systemctl start redis-server
echo "  Redis: $(redis-cli ping)"

# --- PostgreSQL ---
echo ""
echo "[6/9] Installing PostgreSQL 15..."
apt-get install -y postgresql postgresql-contrib
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'linkedin_bot') THEN
    CREATE USER linkedin_bot WITH PASSWORD 'linkedin_bot_pass';
  END IF;
END
\$\$;

CREATE DATABASE linkedin_bot OWNER linkedin_bot;
GRANT ALL PRIVILEGES ON DATABASE linkedin_bot TO linkedin_bot;
SQL
echo "  PostgreSQL database 'linkedin_bot' created."
echo "  WARNING: Change the DB password in .env and update PostgreSQL:"
echo "    sudo -u postgres psql -c \"ALTER USER linkedin_bot PASSWORD 'YOUR_STRONG_PASSWORD';\""

# --- Clone repository ---
echo ""
echo "[7/9] Cloning repository..."
if [ -d "$APP_PATH" ]; then
    echo "  Directory $APP_PATH already exists. Pulling latest..."
    cd "$APP_PATH"
    sudo -u linkedin git pull
else
    sudo -u linkedin git clone "$REPO_URL" "$APP_PATH"
fi

# --- Python virtual environment + dependencies ---
echo ""
echo "[8/9] Setting up Python virtual environment..."
sudo -u linkedin bash <<VENV
cd $APP_PATH
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
VENV
echo "  Python dependencies installed."

# --- Nginx reverse proxy for payment server ---
echo ""
echo "[9/9] Configuring Nginx (payment server on port 5000 → port 80)..."
cat > /etc/nginx/sites-available/linkedin-bot <<NGINX
server {
    listen 80;
    server_name $SERVER_IP _;

    # Payment server
    location /payment/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-enabled/linkedin-bot
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
systemctl enable nginx

# --- Firewall ---
echo ""
echo "Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "  Firewall: SSH(22), HTTP(80), HTTPS(443) allowed."
echo "  Port 5000 is NOT exposed publicly (proxied via Nginx)."

# --- Create data directories ---
echo ""
sudo -u linkedin mkdir -p "$APP_PATH/data"
sudo -u linkedin mkdir -p "$APP_PATH/screenshots"
sudo -u linkedin mkdir -p "$APP_PATH/cookies"
sudo -u linkedin mkdir -p "$APP_PATH/logs"

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Upload your .env file:"
echo "   scp .env root@$SERVER_IP:$APP_PATH/.env"
echo ""
echo "2. Update .env on the server — change these values:"
echo "   HEADLESS=True"
echo "   DATABASE_HOST=localhost"
echo "   DATABASE_USER=linkedin_bot"
echo "   DATABASE_PASSWORD=linkedin_bot_pass   ← change this!"
echo "   DATABASE_NAME=linkedin_bot"
echo "   PAYMENT_SERVER_URL=http://$SERVER_IP"
echo "   WEBAPP_URL=http://$SERVER_IP"
echo ""
echo "3. Run the database schema:"
echo "   cd $APP_PATH && source venv/bin/activate"
echo "   python setup_database_interactive.py"
echo ""
echo "4. Install and start services:"
echo "   bash deployment/2_install_services.sh"
echo ""
echo "5. (Optional) Migrate your local database:"
echo "   See deployment/migrate_db_export.bat (run on Windows)"
echo "   Then: bash deployment/migrate_db_import.sh"
echo ""

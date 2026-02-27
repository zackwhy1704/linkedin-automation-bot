#!/bin/bash
# =============================================================================
# LinkedIn Bot - Import Database on Server
# Run this on the server after uploading linkedin_bot_export.sql
# Usage: bash deployment/migrate_db_import.sh
# =============================================================================
set -e

APP_PATH="/home/linkedin/linkedin-automation-bot"
EXPORT_FILE="$APP_PATH/linkedin_bot_export.sql"

echo ""
echo "=============================================="
echo "  LinkedIn Bot - Import Database"
echo "=============================================="

if [ ! -f "$EXPORT_FILE" ]; then
    echo ""
    echo "ERROR: Export file not found at $EXPORT_FILE"
    echo ""
    echo "Upload it first:"
    echo "  scp linkedin_bot_export.sql root@THIS_SERVER:$APP_PATH/"
    exit 1
fi

echo ""
echo "Importing database from $EXPORT_FILE..."
echo "(This will REPLACE any existing data in linkedin_bot database)"
echo ""
read -p "Continue? [y/N]: " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

# Drop and recreate the database
sudo -u postgres psql <<SQL
DROP DATABASE IF EXISTS linkedin_bot;
CREATE DATABASE linkedin_bot OWNER linkedin_bot;
GRANT ALL PRIVILEGES ON DATABASE linkedin_bot TO linkedin_bot;
SQL

# Import the data
sudo -u postgres psql -d linkedin_bot -f "$EXPORT_FILE"

echo ""
echo "[OK] Database imported successfully."
echo ""
echo "Restart services to reconnect:"
echo "  systemctl restart telegram-bot celery-worker payment-server"
echo ""

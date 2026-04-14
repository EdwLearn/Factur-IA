#!/bin/bash

# ===================================================================
# Setup Automated Backups with Cron - FacturIA
# ===================================================================
# This script configures automated database backups using cron
# Usage: ./setup_automated_backups.sh
# ===================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="${SCRIPT_DIR}/backup_database.sh"

echo "======================================================================"
echo "          Setup Automated Database Backups - FacturIA"
echo "======================================================================"
echo ""

# Check if backup script exists
if [ ! -f "${BACKUP_SCRIPT}" ]; then
    echo -e "${RED}❌ Error: Backup script not found at ${BACKUP_SCRIPT}${NC}"
    exit 1
fi

# Make sure backup script is executable
chmod +x "${BACKUP_SCRIPT}"

echo "📋 Available backup schedules:"
echo ""
echo "1. Every hour (recommended for production)"
echo "2. Every 6 hours (recommended for development)"
echo "3. Daily at 2 AM (minimal frequency)"
echo "4. Daily at midnight (end of day)"
echo "5. Twice daily (6 AM and 6 PM)"
echo "6. Custom schedule"
echo "7. Remove automated backups"
echo ""
echo -n "Select an option (1-7): "
read -r OPTION

case $OPTION in
    1)
        CRON_SCHEDULE="0 * * * *"
        DESCRIPTION="every hour"
        ;;
    2)
        CRON_SCHEDULE="0 */6 * * *"
        DESCRIPTION="every 6 hours"
        ;;
    3)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="daily at 2 AM"
        ;;
    4)
        CRON_SCHEDULE="0 0 * * *"
        DESCRIPTION="daily at midnight"
        ;;
    5)
        CRON_SCHEDULE="0 6,18 * * *"
        DESCRIPTION="twice daily (6 AM and 6 PM)"
        ;;
    6)
        echo ""
        echo "Enter custom cron schedule (e.g., '0 */2 * * *' for every 2 hours):"
        read -r CRON_SCHEDULE
        DESCRIPTION="custom schedule: ${CRON_SCHEDULE}"
        ;;
    7)
        echo ""
        echo "🗑️  Removing automated backups..."
        crontab -l 2>/dev/null | grep -v "${BACKUP_SCRIPT}" | crontab - || true
        echo -e "${GREEN}✅ Automated backups removed${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

# Add to crontab
echo ""
echo "⚙️  Setting up automated backup with schedule: ${DESCRIPTION}"
echo "   Cron expression: ${CRON_SCHEDULE}"
echo ""

# Remove existing backup job if any
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v "${BACKUP_SCRIPT}" > "${TEMP_CRON}" || true

# Add new backup job
echo "${CRON_SCHEDULE} ${BACKUP_SCRIPT} auto >> ${SCRIPT_DIR}/backup.log 2>&1" >> "${TEMP_CRON}"

# Install new crontab
crontab "${TEMP_CRON}"
rm "${TEMP_CRON}"

echo -e "${GREEN}✅ Automated backups configured successfully!${NC}"
echo ""
echo "📊 Backup Details:"
echo "   • Schedule: ${DESCRIPTION}"
echo "   • Script: ${BACKUP_SCRIPT}"
echo "   • Log file: ${SCRIPT_DIR}/backup.log"
echo ""
echo "💡 Current crontab:"
crontab -l | grep -E "backup_database|#"
echo ""
echo "======================================================================"
echo "To view backup logs:"
echo "   tail -f ${SCRIPT_DIR}/backup.log"
echo ""
echo "To manually run backup:"
echo "   ${BACKUP_SCRIPT} manual"
echo ""
echo "To remove automated backups:"
echo "   $0  (and select option 7)"
echo "======================================================================"
echo ""

exit 0

#!/bin/bash

# ===================================================================
# PostgreSQL Database Backup Script for FacturIA
# ===================================================================
# This script creates automated backups of the PostgreSQL database
# Usage: ./backup_database.sh [manual|auto]
# ===================================================================

set -e  # Exit on error

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "❌ Error: .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

# Configuration
BACKUP_DIR="${PROJECT_ROOT}/backups/database"
BACKUP_TYPE="${1:-auto}"  # manual or auto (default: auto)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_FOLDER=$(date +"%Y-%m")
RETENTION_DAYS=30  # Keep backups for 30 days

# Database connection
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-facturia_dev}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD}"

# Backup file naming
if [ "$BACKUP_TYPE" = "manual" ]; then
    BACKUP_NAME="manual_backup_${TIMESTAMP}.sql"
else
    BACKUP_NAME="auto_backup_${TIMESTAMP}.sql"
fi

BACKUP_PATH="${BACKUP_DIR}/${DATE_FOLDER}"
BACKUP_FILE="${BACKUP_PATH}/${BACKUP_NAME}"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "          PostgreSQL Database Backup - FacturIA"
echo "======================================================================"
echo ""
echo "📅 Date: $(date)"
echo "🗄️  Database: ${DB_NAME}"
echo "🖥️  Host: ${DB_HOST}:${DB_PORT}"
echo "📂 Backup Directory: ${BACKUP_PATH}"
echo "📝 Backup Type: ${BACKUP_TYPE}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_PATH}"

# Check if PostgreSQL tools are available
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ Error: pg_dump command not found${NC}"
    echo "Please install PostgreSQL client tools"
    exit 1
fi

# Check database connectivity
echo "🔍 Checking database connectivity..."
export PGPASSWORD="${DB_PASSWORD}"

if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Cannot connect to database${NC}"
    echo "Please check your database configuration"
    exit 1
fi

echo -e "${GREEN}✅ Database connection successful${NC}"
echo ""

# Create backup
echo "💾 Creating database backup..."
echo "   This may take a few minutes depending on database size..."
echo ""

START_TIME=$(date +%s)

# Perform backup with verbose output
pg_dump -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --verbose \
        --file="${BACKUP_FILE}" \
        --no-owner \
        --no-privileges 2>&1 | grep -E "^pg_dump: |^$" || true

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ Error: Backup file was not created${NC}"
    exit 1
fi

# Compress backup
echo ""
echo "🗜️  Compressing backup..."
gzip "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE_GZ}" | cut -f1)

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Backup completed successfully!${NC}"
echo "======================================================================"
echo ""
echo "📊 Backup Details:"
echo "   • File: ${BACKUP_NAME}.gz"
echo "   • Location: ${BACKUP_PATH}"
echo "   • Size: ${BACKUP_SIZE}"
echo "   • Duration: ${DURATION} seconds"
echo ""

# Cleanup old backups
echo "🧹 Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}   Deleted ${DELETED_COUNT} old backup(s)${NC}"
else
    echo "   No old backups to delete"
fi

echo ""

# List recent backups
echo "📋 Recent backups:"
find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime -7 -exec ls -lh {} \; | \
    awk '{print "   •", $9, "-", $5, "-", $6, $7, $8}' | sort -r | head -n 10

echo ""
echo "======================================================================"
echo "💡 To restore this backup, use:"
echo "   ./restore_database.sh ${BACKUP_FILE_GZ}"
echo "======================================================================"
echo ""

# Cleanup password from environment
unset PGPASSWORD

exit 0

#!/bin/bash

# ===================================================================
# PostgreSQL Database Restore Script for FacturIA
# ===================================================================
# This script restores a PostgreSQL database from a backup file
# Usage: ./restore_database.sh <backup_file.sql.gz>
# ===================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    find "$(pwd)/../../backups/database" -name "*.sql.gz" 2>/dev/null | sort -r | head -n 10
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo -e "${YELLOW}⚠️  Warning: .env file not found, using defaults${NC}"
fi

# Database connection
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-facturia_dev}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD}"

echo "======================================================================"
echo "          PostgreSQL Database Restore - FacturIA"
echo "======================================================================"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will REPLACE all current data in the database!${NC}"
echo ""
echo "📅 Date: $(date)"
echo "🗄️  Database: ${DB_NAME}"
echo "🖥️  Host: ${DB_HOST}:${DB_PORT}"
echo "📂 Backup File: ${BACKUP_FILE}"
echo ""
echo -n "Are you sure you want to continue? (yes/no): "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo ""
    echo "❌ Restore cancelled by user"
    exit 0
fi

# Check PostgreSQL tools
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ Error: psql command not found${NC}"
    echo "Please install PostgreSQL client tools"
    exit 1
fi

# Check database connectivity
echo ""
echo "🔍 Checking database connectivity..."
export PGPASSWORD="${DB_PASSWORD}"

if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Cannot connect to database${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Database connection successful${NC}"

# Create a safety backup before restore
SAFETY_BACKUP_DIR="${PROJECT_ROOT}/backups/database/pre-restore"
mkdir -p "${SAFETY_BACKUP_DIR}"
SAFETY_BACKUP="${SAFETY_BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql"

echo ""
echo "🔒 Creating safety backup before restore..."
pg_dump -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        --file="${SAFETY_BACKUP}" 2>&1 | grep -v "^$" || true

if [ -f "${SAFETY_BACKUP}" ]; then
    gzip "${SAFETY_BACKUP}"
    echo -e "${GREEN}✅ Safety backup created: ${SAFETY_BACKUP}.gz${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Could not create safety backup${NC}"
fi

# Decompress backup if needed
TEMP_SQL_FILE=""
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo ""
    echo "📦 Decompressing backup file..."
    TEMP_SQL_FILE=$(mktemp)
    gunzip -c "${BACKUP_FILE}" > "${TEMP_SQL_FILE}"
    SQL_FILE="${TEMP_SQL_FILE}"
else
    SQL_FILE="${BACKUP_FILE}"
fi

# Restore database
echo ""
echo "♻️  Restoring database..."
echo "   This may take a few minutes..."
echo ""

START_TIME=$(date +%s)

# Drop all tables and restore
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -f "${SQL_FILE}" 2>&1 | grep -E "^ERROR:|^FATAL:|^WARNING:" || true

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Cleanup temp file
if [ -n "${TEMP_SQL_FILE}" ] && [ -f "${TEMP_SQL_FILE}" ]; then
    rm -f "${TEMP_SQL_FILE}"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Database restore completed!${NC}"
echo "======================================================================"
echo ""
echo "📊 Restore Details:"
echo "   • Duration: ${DURATION} seconds"
echo "   • Database: ${DB_NAME}"
echo ""
echo "💡 Safety backup location:"
echo "   ${SAFETY_BACKUP}.gz"
echo ""
echo "======================================================================"

# Cleanup password from environment
unset PGPASSWORD

exit 0

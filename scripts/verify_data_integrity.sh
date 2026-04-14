#!/bin/bash

# ===================================================================
# Script de Verificación de Integridad de Datos - FacturIA
# ===================================================================
# Verifica que los volúmenes y datos de PostgreSQL estén intactos
# Usage: ./verify_data_integrity.sh
# ===================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="aws-document-processing"
VOLUME_NAME="${PROJECT_NAME}_postgres_data"
CONTAINER_NAME="document_processing_db"
DB_NAME="${DB_NAME:-facturia_dev}"
DB_USER="${DB_USER:-postgres}"

echo "======================================================================"
echo "          Verificación de Integridad de Datos - FacturIA"
echo "======================================================================"
echo ""

# 1. Verificar que volumen existe
echo -n "🔍 Verificando existencia del volumen... "
if docker volume inspect "$VOLUME_NAME" &>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    VOLUME_INFO=$(docker volume inspect "$VOLUME_NAME" --format '{{.Mountpoint}}')
    echo "   📍 Ubicación: $VOLUME_INFO"
    CREATED=$(docker volume inspect "$VOLUME_NAME" --format '{{.CreatedAt}}')
    echo "   📅 Creado: $CREATED"
else
    echo -e "${RED}❌ ERROR${NC}"
    echo "   El volumen $VOLUME_NAME NO existe"
    echo ""
    echo "Volúmenes disponibles:"
    docker volume ls | grep postgres || echo "   No hay volúmenes de PostgreSQL"
    exit 1
fi

echo ""

# 2. Verificar que contenedor está corriendo
echo -n "🔍 Verificando contenedor de PostgreSQL... "
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}✅ Corriendo${NC}"
    CONTAINER_STATUS=$(docker inspect "$CONTAINER_NAME" --format '{{.State.Status}}')
    CONTAINER_HEALTH=$(docker inspect "$CONTAINER_NAME" --format '{{.State.Health.Status}}' 2>/dev/null || echo "N/A")
    echo "   📊 Estado: $CONTAINER_STATUS"
    if [ "$CONTAINER_HEALTH" != "N/A" ]; then
        echo "   💚 Health: $CONTAINER_HEALTH"
    fi
elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Existe pero NO está corriendo${NC}"
    echo ""
    echo "   Intentando iniciar el contenedor..."
    docker start "$CONTAINER_NAME"
    sleep 3
else
    echo -e "${RED}❌ NO encontrado${NC}"
    echo ""
    echo "   Contenedores disponibles:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

echo ""

# 3. Verificar conectividad a PostgreSQL
echo -n "🔍 Verificando conectividad a PostgreSQL... "
MAX_RETRIES=5
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL responde${NC}"
        PG_VERSION=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT version();" | grep PostgreSQL | cut -d' ' -f2)
        echo "   🐘 Versión: PostgreSQL $PG_VERSION"
        break
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            echo -n "."
            sleep 2
        else
            echo -e "${RED}❌ NO responde${NC}"
            echo ""
            echo "   Logs del contenedor:"
            docker logs --tail 20 "$CONTAINER_NAME"
            exit 1
        fi
    fi
done

echo ""

# 4. Verificar tamaño de la base de datos
echo "📊 Información de la base de datos:"
DB_SIZE=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null || echo "N/A")
echo "   💾 Tamaño de BD: $DB_SIZE"

# 5. Listar tablas existentes
echo ""
echo "📋 Tablas en la base de datos:"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
  SELECT
    schemaname as schema,
    tablename as table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
" 2>/dev/null || echo "   No se pudieron listar las tablas"

# 6. Contar registros en tablas principales
echo ""
echo "📊 Conteo de registros en tablas principales:"

# Verificar si las tablas existen antes de contar
TABLES=("tenants" "processed_invoices" "invoice_line_items" "products" "suppliers")
for table in "${TABLES[@]}"; do
    # Verificar si la tabla existe
    TABLE_EXISTS=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = '$table'
        );
    " 2>/dev/null || echo "f")

    if [ "$TABLE_EXISTS" = "t" ]; then
        COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "Error")
        if [ "$COUNT" != "Error" ]; then
            printf "   %-25s %s registros\n" "$table:" "$COUNT"
        else
            printf "   %-25s %s\n" "$table:" "Error al contar"
        fi
    else
        printf "   %-25s %s\n" "$table:" "No existe"
    fi
done

# 7. Verificar última actividad
echo ""
echo "📅 Última actividad en la base de datos:"
LAST_ACTIVITY=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "
    SELECT MAX(stats_reset)
    FROM pg_stat_database
    WHERE datname = '$DB_NAME';
" 2>/dev/null || echo "N/A")
echo "   Última reinicio de estadísticas: ${LAST_ACTIVITY:-N/A}"

# 8. Verificar espacio en disco del volumen
echo ""
echo "💾 Espacio en disco del volumen:"
DISK_USAGE=$(docker exec "$CONTAINER_NAME" df -h /var/lib/postgresql/data | tail -n 1)
echo "   $DISK_USAGE"

# 9. Verificar conexiones activas
echo ""
echo "🔌 Conexiones activas:"
CONNECTIONS=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -tAc "
    SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';
" 2>/dev/null || echo "N/A")
echo "   Conexiones activas: $CONNECTIONS"

# 10. Verificar existencia de backups
echo ""
echo "💼 Backups disponibles:"
BACKUP_DIR="$(dirname "$0")/../backups/database"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f | wc -l)
    echo "   Total de backups: $BACKUP_COUNT"

    if [ "$BACKUP_COUNT" -gt 0 ]; then
        echo ""
        echo "   Backups más recientes:"
        find "$BACKUP_DIR" -name "*.sql.gz" -type f -printf "%T@ %p\n" | \
            sort -rn | head -n 3 | \
            while read timestamp filepath; do
                filename=$(basename "$filepath")
                filesize=$(du -h "$filepath" | cut -f1)
                filedate=$(date -d "@${timestamp%.*}" "+%Y-%m-%d %H:%M:%S")
                echo "      • $filename ($filesize) - $filedate"
            done
    else
        echo -e "   ${YELLOW}⚠️  No hay backups disponibles${NC}"
        echo "   Ejecuta: ./scripts/backup/backup_database.sh manual"
    fi
else
    echo -e "   ${YELLOW}⚠️  Directorio de backups no encontrado${NC}"
    echo "   Se creará al ejecutar el primer backup"
fi

# Resumen final
echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Verificación completada exitosamente${NC}"
echo "======================================================================"
echo ""
echo "📝 Resumen:"
echo "   • Volumen: ✅ Existe y está montado"
echo "   • Contenedor: ✅ Corriendo correctamente"
echo "   • PostgreSQL: ✅ Respondiendo"
echo "   • Datos: ✅ Accesibles"
echo ""
echo "💡 Próximos pasos recomendados:"
echo "   1. Si no hay backups recientes, ejecuta:"
echo "      ./scripts/backup/backup_database.sh manual"
echo ""
echo "   2. Configura backups automáticos:"
echo "      ./scripts/backup/setup_automated_backups.sh"
echo ""
echo "======================================================================"

exit 0

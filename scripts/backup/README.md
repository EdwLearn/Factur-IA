# Scripts de Backup - FacturIA

## 📦 Contenido

Este directorio contiene scripts para realizar backups y restauración de la base de datos PostgreSQL.

## 🚀 Inicio Rápido

### 1. Backup Manual

```bash
./backup_database.sh manual
```

### 2. Configurar Backups Automáticos

```bash
./setup_automated_backups.sh
```

Selecciona la frecuencia deseada:
- **Opción 1**: Cada hora (producción)
- **Opción 2**: Cada 6 horas (desarrollo) ⭐ Recomendado
- **Opción 3**: Diario a las 2 AM
- **Opción 4**: Diario a medianoche
- **Opción 5**: 2 veces al día (6 AM y 6 PM)
- **Opción 6**: Personalizado
- **Opción 7**: Eliminar backups automáticos

### 3. Restaurar desde Backup

```bash
./restore_database.sh /ruta/al/backup.sql.gz
```

## 📋 Scripts Disponibles

### `backup_database.sh`

Crea un backup completo de la base de datos PostgreSQL.

**Uso**:
```bash
./backup_database.sh [manual|auto]
```

**Características**:
- Compresión automática con gzip
- Nombres de archivo con timestamp
- Organización por mes (YYYY-MM)
- Limpieza automática de backups antiguos (>30 días)
- Verificación de conectividad antes del backup
- Logging detallado

**Ubicación de backups**:
```
aws-document-processing/
├── backups/
│   └── database/
│       ├── 2026-01/
│       │   ├── manual_backup_20260121_143022.sql.gz
│       │   └── auto_backup_20260121_120001.sql.gz
│       └── 2026-02/
│           └── ...
```

**Variables de entorno requeridas** (desde `.env`):
- `DB_HOST`: Host de PostgreSQL (default: localhost)
- `DB_PORT`: Puerto de PostgreSQL (default: 5432)
- `DB_NAME`: Nombre de la base de datos (default: facturia_dev)
- `DB_USER`: Usuario de PostgreSQL (default: postgres)
- `DB_PASSWORD`: Contraseña de PostgreSQL

---

### `restore_database.sh`

Restaura la base de datos desde un archivo de backup.

**Uso**:
```bash
./restore_database.sh /ruta/al/backup.sql.gz
```

**Características**:
- Confirmación obligatoria antes de restaurar
- Backup de seguridad automático antes de restaurar
- Descompresión automática de archivos .gz
- Validación de archivo de backup
- Logging de todo el proceso

**⚠️ ADVERTENCIA**: Este script REEMPLAZA todos los datos actuales en la base de datos.

**Backup de seguridad**:
Antes de cada restauración, se crea automáticamente un backup en:
```
backups/database/pre-restore/pre_restore_YYYYMMDD_HHMMSS.sql.gz
```

---

### `setup_automated_backups.sh`

Configura backups automáticos usando cron.

**Uso**:
```bash
./setup_automated_backups.sh
```

**Características**:
- Interfaz interactiva para seleccionar frecuencia
- Configuración automática de cron
- Logging a archivo (`backup.log`)
- Fácil eliminación de backups automáticos

**Log de backups automáticos**:
```bash
# Ver logs en tiempo real
tail -f backup.log

# Ver últimas 50 líneas
tail -n 50 backup.log
```

---

## 🛠️ Requisitos

### Herramientas Necesarias

- PostgreSQL client tools (`psql`, `pg_dump`, `pg_isready`)
- `gzip` (normalmente preinstalado)
- `cron` (para backups automáticos)
- Bash 4.0 o superior

### Instalación de PostgreSQL Client Tools

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install postgresql-client
```

**MacOS**:
```bash
brew install postgresql
```

**Verificar instalación**:
```bash
pg_dump --version
psql --version
```

---

## 📊 Gestión de Backups

### Ver Backups Disponibles

```bash
# Listar todos los backups
find ../../backups/database -name "*.sql.gz" -ls

# Listar backups de los últimos 7 días
find ../../backups/database -name "*.sql.gz" -mtime -7 -ls

# Ver tamaño total de backups
du -sh ../../backups/database/
```

### Eliminar Backups Antiguos Manualmente

```bash
# Eliminar backups de más de 60 días
find ../../backups/database -name "*.sql.gz" -mtime +60 -delete
```

### Verificar Integridad de un Backup

```bash
# Descomprimir y verificar (sin restaurar)
gunzip -c backup.sql.gz | head -n 50
```

---

## 🔧 Configuración Avanzada

### Cambiar Retención de Backups

Editar `backup_database.sh` línea 19:
```bash
RETENTION_DAYS=30  # Cambiar a los días deseados
```

### Cambiar Ubicación de Backups

Editar `backup_database.sh` línea 16:
```bash
BACKUP_DIR="${PROJECT_ROOT}/backups/database"  # Cambiar ruta
```

### Personalizar Frecuencia de Backups Automáticos

Editar crontab manualmente:
```bash
crontab -e
```

Ejemplos de expresiones cron:
```cron
# Cada hora
0 * * * * /ruta/al/backup_database.sh auto

# Cada 2 horas
0 */2 * * * /ruta/al/backup_database.sh auto

# Cada día a las 3 AM
0 3 * * * /ruta/al/backup_database.sh auto

# Cada lunes a las 2 AM
0 2 * * 1 /ruta/al/backup_database.sh auto
```

---

## 🆘 Solución de Problemas

### Error: "pg_dump command not found"

**Solución**: Instalar PostgreSQL client tools
```bash
sudo apt-get install postgresql-client
```

### Error: "Cannot connect to database"

**Verificar**:
1. PostgreSQL está corriendo:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Credenciales en `.env` son correctas

3. Puerto no está bloqueado:
   ```bash
   nc -zv localhost 5432
   ```

### Error: "Permission denied"

**Solución**: Dar permisos de ejecución
```bash
chmod +x backup_database.sh restore_database.sh setup_automated_backups.sh
```

### Error: "No space left on device"

**Solución**: Limpiar backups antiguos
```bash
find ../../backups/database -name "*.sql.gz" -mtime +30 -delete
```

### Los backups automáticos no se ejecutan

**Verificar cron**:
```bash
# Ver tareas programadas
crontab -l

# Ver logs del sistema
grep CRON /var/log/syslog | tail -n 20

# Ver logs de backup
tail -f backup.log
```

---

## 📚 Casos de Uso

### Caso 1: Backup Antes de Actualización

```bash
# 1. Crear backup manual
./backup_database.sh manual

# 2. Aplicar actualización
cd ../..
git pull origin main

# 3. Si algo falla, restaurar
cd scripts/backup
./restore_database.sh ../../backups/database/YYYY-MM/manual_backup_*.sql.gz
```

### Caso 2: Migrar Base de Datos

```bash
# 1. En servidor origen, crear backup
./backup_database.sh manual

# 2. Copiar archivo a servidor destino
scp backup.sql.gz usuario@destino:/ruta/

# 3. En servidor destino, restaurar
./restore_database.sh /ruta/backup.sql.gz
```

### Caso 3: Probar Cambios Destructivos

```bash
# 1. Backup
./backup_database.sh manual

# 2. Hacer cambios (ej: migración de Alembic)
cd ../../apps/api
alembic upgrade head

# 3. Si hay problemas, rollback
cd ../../scripts/backup
./restore_database.sh ../../backups/database/*/manual_backup_latest.sql.gz
```

---

## 🔐 Seguridad

### Proteger Backups

```bash
# Cambiar permisos (solo dueño puede leer)
chmod 600 ../../backups/database/**/*.sql.gz

# Encriptar backup (opcional)
gpg --symmetric --cipher-algo AES256 backup.sql.gz
```

### Variables de Entorno Sensibles

El script lee `DB_PASSWORD` desde `.env`. **NO** colocar credenciales en el script.

### Backups Externos

Considera sincronizar backups a almacenamiento externo:

```bash
# AWS S3
aws s3 sync ../../backups/database/ s3://mi-bucket/backups/

# rsync a servidor remoto
rsync -avz ../../backups/database/ usuario@servidor:/backups/
```

---

## 📝 Checklist de Mantenimiento

### Diario
- [ ] Verificar que backups automáticos se ejecutaron
- [ ] Revisar `backup.log` para errores

### Semanal
- [ ] Verificar espacio en disco
- [ ] Probar restauración de un backup aleatorio

### Mensual
- [ ] Limpiar backups antiguos (>30 días)
- [ ] Actualizar documentación si hay cambios

---

## 📞 Soporte

Para problemas relacionados con backups:

1. Revisar [DATABASE_SAFETY_POLICY.md](../../DATABASE_SAFETY_POLICY.md)
2. Verificar logs: `cat backup.log`
3. Consultar troubleshooting en esta documentación

---

**Última actualización**: 2026-01-21
**Versión**: 1.0

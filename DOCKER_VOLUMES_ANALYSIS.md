# Análisis de Volúmenes Docker - Persistencia de Datos

## 🎯 Pregunta Clave

**¿Los datos de la BD se guardan en local y NO se borran cuando hay una actualización de volúmenes de Docker?**

### ✅ **RESPUESTA: SÍ, LOS DATOS ESTÁN SEGUROS**

Los datos de PostgreSQL están correctamente configurados para persistir en el sistema local y **NO se borrarán** con actualizaciones de código o contenedores.

---

## 📊 Análisis Detallado de Configuración

### 1. ✅ Volúmenes Named (Persistentes)

Tu proyecto usa **Named Volumes** de Docker, que son la forma **MÁS SEGURA** de persistir datos:

#### **docker-compose.yml** (raíz)
```yaml
# Líneas 12-13
volumes:
  - postgres_data:/var/lib/postgresql/data

# Líneas 113-114
volumes:
  postgres_data:  # ← Named volume (persiste entre reinicios)
```

#### **docker-compose.dev.yml**
```yaml
# Líneas 12-13
volumes:
  - postgres_dev_data:/var/lib/postgresql/data

# Líneas 113-114
volumes:
  postgres_dev_data:  # ← Named volume separado para desarrollo
```

#### **docker-compose.yml** (producción)
```yaml
# Líneas 12-13
volumes:
  - postgres_data:/var/lib/postgresql/data

# Líneas 89-92
volumes:
  postgres_data:
    driver: local  # ← Explícitamente persistente
```

---

### 2. ✅ Verificación de Volúmenes Existentes

**Estado actual del sistema**:

```bash
$ docker volume ls
DRIVER    VOLUME NAME
local     aws-document-processing_postgres_data
local     document-processing-system_postgres_data
```

**Detalles del volumen**:
```json
{
  "Name": "aws-document-processing_postgres_data",
  "Driver": "local",
  "Mountpoint": "/var/lib/docker/volumes/aws-document-processing_postgres_data/_data",
  "CreatedAt": "2026-01-05T22:03:31-05:00"
}
```

**✅ SIGNIFICADO**:
- El volumen **YA EXISTE** y contiene datos desde el 5 de enero 2026
- Ubicación física: `/var/lib/docker/volumes/aws-document-processing_postgres_data/_data`
- Driver `local`: datos guardados en **disco local del host**

---

## 🔒 ¿Qué Operaciones NO Borran los Datos?

### ✅ SEGURAS (NO borran datos)

| Operación | Comando | ¿Borra datos? | Explicación |
|-----------|---------|---------------|-------------|
| Actualizar código | `git pull` | ❌ NO | Solo afecta archivos de código |
| Rebuild contenedor | `docker-compose build` | ❌ NO | Solo reconstruye imagen |
| Restart contenedor | `docker-compose restart` | ❌ NO | Contenedor reutiliza volumen |
| Stop/Start | `docker-compose stop/start` | ❌ NO | Volumen permanece intacto |
| Down (sin -v) | `docker-compose down` | ❌ NO | Volumen persiste |
| Recreate | `docker-compose up --force-recreate` | ❌ NO | Volumen reutilizado |
| Rebuild API | `docker-compose up --build api` | ❌ NO | Solo afecta imagen API |

### ⚠️ PELIGROSAS (pueden borrar datos)

| Operación | Comando | ¿Borra datos? | Explicación |
|-----------|---------|---------------|-------------|
| Down con -v | `docker-compose down -v` | ⚠️ **SÍ** | Elimina volúmenes explícitamente |
| Volume rm | `docker volume rm postgres_data` | ⚠️ **SÍ** | Elimina volumen específico |
| Prune | `docker volume prune` | ⚠️ **SÍ** | Elimina volúmenes no usados |
| System prune | `docker system prune -a --volumes` | ⚠️ **SÍ** | Limpieza total (muy destructivo) |

---

## 🛡️ Protección Incorporada

### 1. Named Volumes vs Bind Mounts

Tu configuración usa **Named Volumes**, NO bind mounts:

```yaml
# ✅ TU CONFIGURACIÓN (Named Volume - SEGURO)
volumes:
  - postgres_data:/var/lib/postgresql/data

# ❌ SI USARAS BIND MOUNT (menos seguro)
volumes:
  - ./data/postgres:/var/lib/postgresql/data  # ← NO es tu caso
```

**Ventajas de Named Volumes**:
- Docker gestiona automáticamente el almacenamiento
- No dependen de la estructura del proyecto
- Protegidos contra eliminaciones accidentales de carpetas
- Mejor rendimiento en Windows/Mac
- Backups más fáciles con `docker volume backup`

### 2. Separación por Entorno

Tu proyecto tiene **volúmenes separados** por entorno:

```yaml
# Desarrollo
postgres_dev_data: ...

# Producción
postgres_data: ...

# Root (otro ambiente)
postgres_data: ...
```

**✅ BENEFICIO**: Actualizar desarrollo NO afecta producción

---

## 📍 Ubicación Física de los Datos

### Linux (tu sistema)

```bash
# Ubicación del volumen
/var/lib/docker/volumes/aws-document-processing_postgres_data/_data

# Estructura interna (PostgreSQL)
_data/
├── base/           # Tablas y datos
├── global/         # Info del cluster
├── pg_wal/         # Write-Ahead Logs
├── pg_stat/        # Estadísticas
└── postgresql.conf # Configuración
```

### Verificar espacio usado

```bash
# Listar volúmenes con tamaño (requiere permisos)
sudo du -sh /var/lib/docker/volumes/aws-document-processing_postgres_data/_data

# Alternativa: desde el contenedor
docker exec document_processing_db du -sh /var/lib/postgresql/data
```

---

## 🔄 Ciclo de Vida de los Volúmenes

### Escenario 1: Actualización Normal de Código

```bash
# 1. Pull código nuevo
git pull origin main

# 2. Rebuild y restart
docker-compose build
docker-compose up -d

# RESULTADO: ✅ Datos intactos, solo código actualizado
```

**¿Por qué es seguro?**
- `build` solo reconstruye la **imagen del contenedor** (código + dependencias)
- El volumen `postgres_data` **NO se toca**
- Al iniciar, PostgreSQL monta el **mismo volumen** con todos los datos

### Escenario 2: Cambio de Esquema con Alembic

```bash
# 1. Pull código con nueva migración
git pull origin main

# 2. Rebuild API
docker-compose build api

# 3. Restart (entrypoint ejecuta Alembic)
docker-compose up -d api

# RESULTADO: ✅ Datos migrados, NO borrados
```

**Flujo interno**:
1. Contenedor inicia
2. `entrypoint.sh` ejecuta: `alembic upgrade head`
3. Alembic **modifica** esquema (agrega/altera tablas)
4. **NUNCA** ejecuta `DROP DATABASE` o `TRUNCATE`

Ver [scripts/entrypoint.sh](scripts/entrypoint.sh:3):
```bash
python -m alembic -c alembic.ini upgrade head || true
```

### Escenario 3: Recreación Total de Contenedores

```bash
# Destruir TODO (contenedores, redes, imágenes)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# RESULTADO: ✅ Datos intactos
# El volumen postgres_data NO se elimina con 'down'
```

---

## 🚨 Única Forma de Perder Datos

### Comando Peligroso #1
```bash
docker-compose down -v
                    # ↑ Flag -v elimina volúmenes
```

### Comando Peligroso #2
```bash
docker volume rm aws-document-processing_postgres_data
```

### Comando Peligroso #3
```bash
docker system prune -a --volumes
                        # ↑ Elimina TODOS los volúmenes no usados
```

**⚠️ PROTECCIÓN**: Docker pregunta confirmación antes de ejecutar estos comandos.

---

## 🛡️ Mejores Prácticas Implementadas

### ✅ Tu configuración cumple con:

1. **Named Volumes** para persistencia
2. **Separación de entornos** (dev/prod)
3. **No bind mounts** para datos críticos
4. **Healthchecks** para verificar estado de BD
5. **Depends_on** para orden de inicio correcto

### ⚠️ Recomendaciones adicionales:

1. **Backups automáticos** ✅ Ya implementados en [scripts/backup/](scripts/backup/)
2. **Monitoreo de espacio de volúmenes**
3. **Labels para identificar volúmenes críticos**

---

## 📋 Comandos Útiles de Gestión

### Listar Volúmenes
```bash
# Todos los volúmenes
docker volume ls

# Volúmenes del proyecto
docker volume ls | grep aws-document-processing

# Detalles de un volumen
docker volume inspect aws-document-processing_postgres_data
```

### Backup de Volumen (método Docker)
```bash
# Backup completo del volumen
docker run --rm \
  -v aws-document-processing_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  busybox tar czf /backup/postgres_volume_backup_$(date +%Y%m%d).tar.gz /data

# Restaurar desde backup
docker run --rm \
  -v aws-document-processing_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  busybox tar xzf /backup/postgres_volume_backup_YYYYMMDD.tar.gz -C /
```

### Verificar Uso de Espacio
```bash
# Espacio total de volúmenes
docker system df -v

# Espacio específico de PostgreSQL
docker exec document_processing_db df -h /var/lib/postgresql/data
```

### Exportar/Importar Volumen a Otra Máquina
```bash
# En máquina origen
docker run --rm \
  -v aws-document-processing_postgres_data:/data \
  busybox tar czf - /data > postgres_data.tar.gz

# Copiar archivo a máquina destino
scp postgres_data.tar.gz user@destino:/ruta/

# En máquina destino
cat postgres_data.tar.gz | docker run --rm -i \
  -v aws-document-processing_postgres_data:/data \
  busybox tar xzf - -C /
```

---

## 🔍 Verificación de Integridad

### Script de Verificación
```bash
#!/bin/bash
# verify_data_integrity.sh

echo "🔍 Verificando integridad de datos..."

# 1. Verificar que volumen existe
if docker volume inspect aws-document-processing_postgres_data &>/dev/null; then
    echo "✅ Volumen existe"
else
    echo "❌ Volumen NO encontrado"
    exit 1
fi

# 2. Verificar que contenedor está corriendo
if docker ps | grep -q document_processing_db; then
    echo "✅ Contenedor de BD está corriendo"
else
    echo "⚠️  Contenedor de BD NO está corriendo"
fi

# 3. Verificar conectividad a BD
if docker exec document_processing_db pg_isready -U postgres -d facturia_dev &>/dev/null; then
    echo "✅ PostgreSQL responde correctamente"
else
    echo "❌ PostgreSQL NO responde"
    exit 1
fi

# 4. Contar registros en tablas principales
echo ""
echo "📊 Conteo de registros:"
docker exec document_processing_db psql -U postgres -d facturia_dev -c "
  SELECT
    'tenants' as table, COUNT(*) as records FROM tenants
  UNION ALL
  SELECT
    'processed_invoices', COUNT(*) FROM processed_invoices
  UNION ALL
  SELECT
    'invoice_line_items', COUNT(*) FROM invoice_line_items
  UNION ALL
  SELECT
    'products', COUNT(*) FROM products;
" -t

echo ""
echo "✅ Verificación completada"
```

---

## 📚 Documentación de Referencia

### Archivos Docker Analizados

| Archivo | Líneas Críticas | Propósito |
|---------|-----------------|-----------|
| [docker-compose.yml](docker-compose.yml) | 12-13, 113-114 | Volumen principal postgres_data |
| [infrastructure/docker-compose/docker-compose.yml](infrastructure/docker-compose/docker-compose.yml) | 12-13, 89-92 | Volumen producción |
| [infrastructure/docker-compose/docker-compose.dev.yml](infrastructure/docker-compose/docker-compose.dev.yml) | 12-13, 113-116 | Volumen desarrollo |
| [scripts/entrypoint.sh](scripts/entrypoint.sh) | 3 | Ejecución de migraciones |
| [Dockerfile](Dockerfile) | 1-38 | Build de API (no toca BD) |

### Enlaces Útiles

- [Docker Volumes Documentation](https://docs.docker.com/storage/volumes/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Docker Compose Volumes](https://docs.docker.com/compose/compose-file/compose-file-v3/#volumes)

---

## ✅ Conclusiones

### Respuestas Directas

1. **¿Los datos se guardan en local?**
   - ✅ **SÍ**: `/var/lib/docker/volumes/aws-document-processing_postgres_data/_data`

2. **¿Se borran con actualizaciones de código?**
   - ✅ **NO**: `docker-compose build` y `docker-compose up` NO afectan volúmenes

3. **¿Se borran al hacer down?**
   - ✅ **NO** (a menos que uses el flag `-v` explícitamente)

4. **¿Se borran al recrear contenedores?**
   - ✅ **NO**: Contenedor nuevo monta el mismo volumen

5. **¿Qué puede borrarlos?**
   - ⚠️ Solo comandos explícitos: `docker-compose down -v`, `docker volume rm`, `docker volume prune`

### Estado Actual: 🟢 SEGURO

Tu configuración es **robusta** y sigue las mejores prácticas de Docker para persistencia de datos.

### Recomendaciones Finales

1. ✅ **Backups automáticos**: Ya implementados en [scripts/backup/](scripts/backup/)
2. ✅ **Named volumes**: Correctamente configurados
3. ✅ **Separación de entornos**: Dev y prod separados
4. 📝 **Documentar en README**: Agregar advertencias sobre `-v` flag
5. 🔄 **Monitoreo**: Considerar alertas si volumen se llena

---

## 🚀 Flujo de Trabajo Seguro

```bash
# Actualización diaria típica
git pull origin main                    # ✅ Seguro
docker-compose build api                # ✅ Seguro
docker-compose up -d                    # ✅ Seguro

# Limpieza de imágenes viejas (NO volúmenes)
docker image prune -a                   # ✅ Seguro

# Backup antes de operaciones mayores
./scripts/backup/backup_database.sh     # ✅ Recomendado

# Verificar estado
docker-compose ps                       # ✅ Siempre útil
docker volume ls | grep postgres        # ✅ Verificar volumen existe
```

---

**Documento creado**: 2026-01-21
**Última revisión**: 2026-01-21
**Próxima revisión**: 2026-02-21
**Versión**: 1.0

**Estado**: ✅ **DATOS SEGUROS Y PERSISTENTES**

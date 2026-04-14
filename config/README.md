# Configuration Management

Esta carpeta contiene las configuraciones de environment para FacturIA.

## Estructura

```
config/
├── environments/          # Archivos de configuración por ambiente
│   ├── .env.development  # Desarrollo local
│   ├── .env.test        # Testing
│   ├── .env.staging     # Staging
│   └── .env.production  # Producción
└── secrets/              # Secrets locales (.gitignored)
    ├── .env.development.local
    ├── .env.staging.local
    └── .env.production.local
```

## Uso

### Desarrollo Local

1. Copiar el archivo de desarrollo al root:
   ```bash
   cp config/environments/.env.development .env
   ```

2. Crear archivo de secrets locales (opcional):
   ```bash
   cp config/environments/.env.development config/secrets/.env.development.local
   ```

3. Editar `.env` con tus valores locales:
   ```bash
   DB_PASSWORD=tu_password_local
   AWS_ACCESS_KEY_ID=tu_access_key
   AWS_SECRET_ACCESS_KEY=tu_secret_key
   SECRET_KEY=tu_jwt_secret
   ```

### Testing

Para tests, las variables se configuran automáticamente en `pytest.ini`:

```ini
[pytest]
env =
    ENVIRONMENT=test
    DB_HOST=localhost
    DB_PORT=5433
    ...
```

### Staging & Production

En ambientes cloud, las variables se configuran en:

1. **AWS ECS Task Definition** - Variables no sensibles
2. **AWS Secrets Manager** - Variables sensibles (passwords, keys)

#### Ejemplo de Task Definition:

```json
{
  "environment": [
    {"name": "ENVIRONMENT", "value": "production"},
    {"name": "DB_HOST", "value": "facturia-prod.xxxxx.rds.amazonaws.com"}
  ],
  "secrets": [
    {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:facturia/db-password"},
    {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:facturia/jwt-secret"}
  ]
}
```

## Variables Requeridas

### Básicas (Todos los ambientes)

- `ENVIRONMENT` - Environment name (development, staging, production, test)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `AWS_REGION`, `S3_DOCUMENT_BUCKET`

### Seguridad (Staging & Production)

- `SECRET_KEY` - JWT signing key (min 32 caracteres, random)
- `DB_PASSWORD` - Database password (strong, rotated)
- `REDIS_PASSWORD` - Redis password (si aplica)

### Opcionales

- `AWS_ENDPOINT_URL` - Para LocalStack (solo development)
- `REDIS_PASSWORD` - Si Redis requiere auth
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR, CRITICAL

## Secrets Management

### Desarrollo

Archivos en `config/secrets/` son ignorados por git. Úsalos para secrets locales.

### Staging & Production

**NUNCA** comitear secrets al repositorio. Usar:

1. **AWS Secrets Manager** (Recomendado):
   ```bash
   aws secretsmanager create-secret \
     --name facturia/production/db-password \
     --secret-string "your-secure-password"
   ```

2. **GitHub Secrets** (Para CI/CD):
   - Settings → Secrets and variables → Actions
   - Agregar: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.

## Validación

El código valida automáticamente la configuración al inicio:

```python
from src.core.config import get_settings

settings = get_settings()  # Raises validation error si falta algo
```

## Referencias

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [12-Factor App Config](https://12factor.net/config)

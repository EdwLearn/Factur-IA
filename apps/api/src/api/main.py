"""
FastAPI application for invoice processing SaaS with PostgreSQL
"""
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables FIRST, before importing settings
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import uvicorn
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from ..core.config import settings
from ..database.connection import init_database, close_database, create_tables, check_database_health
from ..services.storage.cleanup_service import StorageCleanupService
from ..services.integrations.inventory_sync_service import inventory_sync_service
from ..services.sales_sync_service import SalesSyncService
from ..database.models import AlegraConnection
from .routers import invoices, dashboard, inventory, auth, subscriptions, integrations, suppliers, recommendations, admin


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_daily_cleanup() -> None:
    """Background task: elimina archivos S3 expirados una vez cada 24 h."""
    while True:
        await asyncio.sleep(86400)
        try:
            service = StorageCleanupService()
            await service.cleanup_expired_invoices()
        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")


async def _sales_sync_job() -> None:
    """Sincroniza ventas de Alegra → inventory_movements cada 6 horas."""
    logger.info("🛒 Iniciando sincronización de ventas desde Alegra...")
    try:
        from ..database.connection import AsyncSessionFactory
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(AlegraConnection).where(AlegraConnection.is_active == True)
            )
            connections = result.scalars().all()

        service = SalesSyncService()
        for conn in connections:
            try:
                summary = await service.sync_sales_from_alegra(
                    tenant_id=conn.tenant_id,
                    date_start=None,
                )
                logger.info(
                    f"  tenant={conn.tenant_id} synced={summary['synced']} "
                    f"errors={summary['errors']}"
                )
            except Exception as exc:
                logger.error(f"  tenant={conn.tenant_id} falló: {exc}")

        logger.info(f"✅ Sales sync completado para {len(connections)} tenant(s)")
    except Exception as exc:
        logger.error(f"❌ Sales sync job falló: {exc}")


async def _alegra_sync_job() -> None:
    """Sincroniza ítems y contactos con Alegra para todos los tenants activos."""
    logger.info("🔄 Iniciando sincronización periódica con Alegra...")
    try:
        results = await inventory_sync_service.sync_all_tenants()
        total_items = sum(r.total_synced_items for r in results)
        total_contacts = sum(r.synced_contacts for r in results)
        total_errors = sum(len(r.errors) for r in results)
        logger.info(
            f"✅ Sync Alegra completado: {len(results)} tenant(s), "
            f"{total_items} ítems, {total_contacts} contactos, {total_errors} errores"
        )
    except Exception as exc:
        logger.error(f"❌ Sync Alegra job falló: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Invoice SaaS API...")
    await init_database()

    # Auto-create tables in development ONLY.
    # In staging/production the schema is managed by Alembic migrations:
    #   alembic upgrade head
    # Never rely on create_tables() as the source of truth for the schema.
    if settings.environment == "development":
        await create_tables()
        logger.info("📊 Database tables ready (dev auto-create)")

    # Tarea diaria: limpieza de archivos S3 expirados según plan del tenant.
    asyncio.create_task(run_daily_cleanup())
    logger.info("🗑️  Daily S3 cleanup job scheduled (every 24 h)")

    # Scheduler APScheduler: sync Alegra cada 3 horas
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _alegra_sync_job,
        trigger="interval",
        hours=3,
        id="alegra_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _sales_sync_job,
        trigger="interval",
        hours=6,
        id="sales_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("🔄 Alegra sync scheduler iniciado (ítems cada 3 h, ventas cada 6 h)")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    scheduler.shutdown(wait=False)
    await close_database()

# Create FastAPI app
app = FastAPI(
    title="FacturIA - Invoice Processing API",
    description="""
## 🚀 Sistema de Procesamiento Inteligente de Facturas para Retail

API completa para la gestión de facturas, inventario y análisis de datos para negocios retail en Colombia.

### 🔑 Características Principales

* **📄 Procesamiento de Facturas**: Extracción automática de datos con AWS Textract
* **📦 Gestión de Inventario**: Control de stock, movimientos y alertas
* **📊 Dashboard Analítico**: Métricas y análisis en tiempo real
* **🏢 Multi-tenant**: Soporte para múltiples empresas
* **🔄 Integración POS**: Exportación a sistemas Mayasís y otros

### 🔐 Autenticación

Todos los endpoints requieren el header `x-tenant-id` para identificar la empresa.

### 📚 Documentación

* **Swagger UI**: `/docs` (esta página)
* **ReDoc**: `/redoc`
* **Health Check**: `/health`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "FacturIA Support",
        "email": "support@facturia.com",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=[
        {
            "name": "🔐 Auth",
            "description": "Registro de tenants y autenticación JWT"
        },
        {
            "name": "📊 Dashboard",
            "description": "Métricas, análisis y estadísticas del negocio en tiempo real"
        },
        {
            "name": "📄 Invoices",
            "description": "Procesamiento, gestión y análisis de facturas con OCR"
        },
        {
            "name": "📦 Inventory",
            "description": "Gestión completa de inventario, productos y movimientos de stock"
        },
        {
            "name": "🏥 Health",
            "description": "Endpoints de monitoreo y estado del sistema"
        }
    ]
)


ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    *(o for o in [os.getenv("FRONTEND_URL", "")] if o),
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "x-tenant-id",
        "Accept",
    ],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["🔐 Auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["📊 Dashboard"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["📄 Invoices"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["📦 Inventory"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["💳 Subscriptions"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["🔌 Integrations"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["🏢 Suppliers"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["🧠 Recommendations"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["🔒 Admin"])

# Servir archivos estáticos del frontend
if os.path.exists("apps/web/.next/static"):
    app.mount("/static", StaticFiles(directory="apps/web/.next/static"), name="static")

if os.path.exists("apps/web/.next/standalone"):
    app.mount("/frontend", StaticFiles(directory="apps/web/.next/standalone"), name="frontend")

@app.get("/", tags=["🏥 Health"], summary="API Root", description="Información básica de la API")
async def root():
    """
    Endpoint raíz que retorna información básica de la API

    Retorna información sobre la versión, estado y configuración del sistema.
    """
    return {
        "name": "FacturIA API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment,
        "target_market": "Colombian retail stores",
        "database": "PostgreSQL",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["🏥 Health"], summary="Health Check", description="Verificación detallada del estado del sistema")
async def health_check():
    """
    Health check detallado del sistema

    Verifica el estado de todos los servicios:
    - Base de datos PostgreSQL
    - AWS Textract
    - AWS S3
    - Procesador de facturas

    Returns:
        dict: Estado de todos los servicios del sistema
    """
    db_healthy = await check_database_health()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "aws": "configured",
        "services": {
            "textract": "available",
            "s3": "available",
            "invoice_processor": "running",
            "postgresql": "connected" if db_healthy else "disconnected"
        }
    }

def _cors_headers(request) -> dict:
    """Return CORS headers for the request's origin, if allowed."""
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
        headers=_cors_headers(request),
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
        headers=_cors_headers(request),
    )
    

# Ruta catch-all para servir el frontend
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """
    Sirve el frontend de Next.js
    Si no es una ruta de API, devuelve index.html
    """
    # Si es una ruta de API, dejar que FastAPI la maneje
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Si es un archivo estático específico
    static_file_path = f"apps/web/.next/static/{path}"
    if os.path.exists(static_file_path):
        return FileResponse(static_file_path)
    
    # Para cualquier otra ruta, servir el index.html del frontend
    index_path = "apps/web/.next/server/pages/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    # Fallback
    return {"message": "Frontend not found", "path": path}    

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )

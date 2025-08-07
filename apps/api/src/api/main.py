"""
FastAPI application for invoice processing SaaS with PostgreSQL
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager
import os

from ..config.settings import settings
from ..database.connection import init_database, close_database, create_tables, check_database_health
from .routers import invoices
from dotenv import load_dotenv
load_dotenv(".env")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Servir archivos estáticos del frontend
if os.path.exists("apps/web/.next/static"):
    app.mount("/static", StaticFiles(directory="apps/web/.next/static"), name="static")

if os.path.exists("apps/web/.next/standalone"):
    app.mount("/frontend", StaticFiles(directory="apps/web/.next/standalone"), name="frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Invoice SaaS API...")
    await init_database()
    
    # Create tables if needed (development)
    if settings.environment == "development":
        await create_tables()
        logger.info("📊 Database tables ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_database()

# Create FastAPI app
app = FastAPI(
    title="Invoice Processing SaaS API",
    description="Intelligent invoice processing for Colombian retail businesses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Invoice Processing SaaS API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment,
        "target_market": "Colombian retail stores",
        "database": "PostgreSQL"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
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

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
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
        return {"error": "API endpoint not found"}, 404
    
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

"""
Database connection and session management
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from databases import Database
import logging

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Async engine for SQLAlchemy
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.environment == "development",
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Session factory
AsyncSessionFactory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Database instance for direct queries
database = Database(settings.async_database_url)

async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """Initialize database connection"""
    try:
        await database.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

async def close_database():
    """Close database connection"""
    try:
        await database.disconnect()
        logger.info("Database disconnected")
    except Exception as e:
        logger.error(f"Database disconnection failed: {str(e)}")

async def create_tables():
    """Create all tables"""
    from .models import Base
    
    async with engine.begin() as conn:
        # Drop all tables (development only)
        if settings.environment == "development":
            await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Database tables created")

# Health check
async def check_database_health() -> bool:
    """Check database connectivity"""
    try:
        await database.fetch_one("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False

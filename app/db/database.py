"""
Database configuration and connection management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True if settings.ENVIRONMENT == "development" else False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,  # Reduced for Supabase Session Mode (max 15 connections in free tier)
    max_overflow=5,  # Total max = 10 connections
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base with naming convention for constraints
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

Base = declarative_base(metadata=metadata)


async def create_tables():
    """Create all database tables - DISABLED: Using Alembic migrations instead
    
    This function is kept for backwards compatibility but does nothing.
    Database schema is managed via alembic migrations (see alembic/versions/).
    Run 'alembic upgrade head' to apply migrations.
    """
    try:
        # Import all models to ensure they're registered with SQLAlchemy
        from app.models import (
            user, category, livestream, content, media, chatbot, quiz,
            myth_fact, conservation, animal_profile, recommendation, site_setting, discussion, discussion_comment, discussion_engagement, user_badge
        )
        
        # DISABLED: We use Alembic for migrations, not SQLAlchemy's create_all()
        # This prevents conflicts between migrations and direct table creation
        # await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database table creation skipped - using Alembic migrations")
    except Exception as e:
        logger.error(f"Error importing database models: {e}")
        # Don't raise - allow app to continue even if models have issues


async def drop_tables():
    """Drop all database tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")


async def get_db():
    """Database session dependency for FastAPI (without retry)"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db_with_retry(max_retries: int = 5, backoff_seconds: int = 2):
    """
    Database session dependency with automatic retry for Railway cold starts.
    
    Railway's free tier puts the database to sleep after inactivity. This function
    handles the wake-up delay gracefully with exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of connection attempts (default: 5)
        backoff_seconds: Initial backoff duration in seconds (default: 2)
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        Exception: If connection fails after all retry attempts
    """
    import asyncio
    from sqlalchemy.exc import OperationalError
    from sqlalchemy import text
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            async with async_session_factory() as session:
                # Test the connection with a simple query
                await session.execute(text("SELECT 1"))
                yield session
                return
                
        except OperationalError as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = backoff_seconds * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Database connection attempt {attempt + 1} failed, "
                    f"retrying in {wait_time}s (Railway cold start recovery)",
                    error=str(e)
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts",
                    error=str(e)
                )
                raise
        except Exception as e:
            logger.error("Unexpected database error", error=str(e))
            await session.rollback()
            raise
    
    if last_exception:
        raise last_exception


@asynccontextmanager
async def get_db_session():
    """Get database session for dependency injection"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

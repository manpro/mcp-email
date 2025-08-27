from typing import Generator
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, Session
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Optimized database connection with connection pooling
engine = create_engine(
    settings.database_url,
    
    # Connection pool configuration
    pool_size=20,              # Number of connections to maintain
    max_overflow=30,           # Additional connections beyond pool_size
    pool_timeout=30,           # Timeout in seconds to get connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Validate connections before use
    
    # Connection arguments for PostgreSQL
    connect_args={
        "application_name": "rss_intelligence",
        "options": "-c timezone=UTC",
    },
    
    # Logging for debugging (disable in production)
    echo=False,
    echo_pool=False,
    
    # Connection retry settings
    pool_reset_on_return='commit'
)

# Configure session with optimizations
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep objects available after commit
)

def get_db() -> Generator[Session, None, None]:
    """Get database session with proper cleanup and error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def get_db_pool_stats() -> dict:
    """Get database connection pool statistics"""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
        "invalid": pool.invalid(),
    }
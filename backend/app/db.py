import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Use the DATABASE_URL from settings
DATABASE_URL = settings.DATABASE_URL

# Process the DATABASE_URL to make it compatible with asyncpg
# Remove sslmode parameter if present, as it's not directly supported by asyncpg
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Parse the URL
if DATABASE_URL:
    parsed_url = urlparse(DATABASE_URL)
    
    # Convert scheme to asyncpg if needed
    scheme = 'postgresql+asyncpg' if parsed_url.scheme == 'postgresql' else parsed_url.scheme
    
    # Parse and filter the query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Remove problematic parameters
    if 'sslmode' in query_params:
        del query_params['sslmode']
    
    # Rebuild the query string
    query_string = urlencode(query_params, doseq=True)
    
    # Reconstruct the URL
    ASYNC_DATABASE_URL = urlunparse((
        scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        query_string,
        parsed_url.fragment
    ))
    logger.info(f"Database URL configured for asyncpg")
else:
    ASYNC_DATABASE_URL = None
    logger.error("WARNING: DATABASE_URL is not set!")

# Create the engine with optimized pool settings and connection health checks
engine = create_async_engine(
    ASYNC_DATABASE_URL, 
    echo=False,  # Set to True for debugging SQL queries
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_pre_ping=True,  # Enable connection health checks
)

# Create the session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create the base model class
Base = declarative_base()

# Database dependency for FastAPI with connection validation
async def get_db():
    session = AsyncSessionLocal()
    try:
        # Verify the connection is working with a simple query
        try:
            await session.execute(text("SELECT 1"))
            await session.commit()
        except Exception as e:
            logger.error(f"Database connection failed during health check: {e}")
            await session.close()
            # Create a new session after a failure
            session = AsyncSessionLocal()
            
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")

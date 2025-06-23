import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from app.db import engine
from app.api.endpoints import router
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Clipso backend starting up...")
    
    # Setup database and tables
    try:
        from app.models import Base
        
        # Create all tables if they don't exist
        async with engine.begin() as conn:
            # Test the connection
            await conn.execute(text("SELECT 1"))
            
            # Create tables (can be safely called multiple times)
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database connection successful and tables created")
    except Exception as e:
        logger.error(f"Database connection or table creation failed: {e}")
        
    # Log R2 storage configuration
    logger.info("Using R2 cloud storage for file uploads")
    
    # Ready
    logger.info("Clipso backend started up.")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Clipso backend shutting down...")
    
    # Close database connections
    await engine.dispose()
    logger.info("Database connections closed")
    
    logger.info("Clipso backend shutdown complete.")

# Create FastAPI application
app = FastAPI(
    title="Clipso API",
    description="API for Clipso video enhancement",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Create the static directory if it doesn't exist yet
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True)

# Create assets directory if it doesn't exist
assets_dir = os.path.join(static_dir, "assets")
os.makedirs(assets_dir, exist_ok=True)

# Mount static files (built frontend) - with conditional check
try:
    if os.path.exists(assets_dir) and os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"Mounted static assets from {assets_dir}")
    else:
        logger.warning(f"Assets directory {assets_dir} not found or not a directory")
except Exception as e:
    logger.error(f"Error mounting static files: {e}")

# Root endpoint - always serve the frontend index.html for the root path
@app.get("/")
async def serve_root(request: Request):
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        logger.warning(f"Frontend build not found at {index_path}. Make sure to run the deploy script.")
        return JSONResponse(
            status_code=404,
            content={"error": "Frontend not built. Run deploy.sh to build the frontend."}
        )

# Handle all other frontend routes - serve index.html for any non-API route
@app.get("/{full_path:path}")
async def serve_frontend(request: Request, full_path: str):
    # API health check endpoint
    if full_path == "api":
        return {"status": "ok", "message": "Clipso API is running"}
    
    # For all other routes, serve the frontend index.html
    index_path = os.path.join(static_dir, "index.html")
    
    # Check if the requested path exists as a static file
    requested_path = os.path.join(static_dir, full_path)
    if os.path.exists(requested_path) and os.path.isfile(requested_path):
        return FileResponse(requested_path)
    
    # If the file doesn't exist or is a directory, serve index.html for SPA routing
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        logger.warning(f"Frontend build not found at {index_path}. Make sure to run the deploy script.")
        return JSONResponse(
            status_code=404,
            content={"error": "Frontend not built. Run deploy.sh to build the frontend."}
        )
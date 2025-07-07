"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .endpoints import router
from ..config.logging import setup_logging
from ..config.settings import API_TITLE, API_DESCRIPTION, API_VERSION

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        Configured FastAPI application
    """
    # Initialize logging
    setup_logging()
    
    # Create FastAPI application
    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router, prefix="/api")
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {API_TITLE}")
    
    return app

# Create app instance for server to import
app = create_app()

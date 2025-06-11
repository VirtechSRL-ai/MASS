import os
from loguru import logger
import sys

def setup_logging():
    """Configure logging settings for the application."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler for errors
    logger.add(
        "logs/error.log",
        rotation="500 MB",
        retention="10 days",
        level="ERROR"
    )

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Scraping configuration
DEFAULT_MAX_PAGES = 3
SCRAPING_SOURCES = [
    {
        "name": "bing",
        "enabled": True,
        "max_results": 20
    }
]

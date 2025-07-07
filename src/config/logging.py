"""
Logging configuration for the MASS system
"""
import sys
from loguru import logger
from pathlib import Path
from .settings import LOG_CONFIG

def setup_logging():
    """
    Configure application logging with Loguru.
    Sets up both console and file logging with appropriate formatting and levels.
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    logger.add(
        sys.stdout,
        format=LOG_CONFIG["format"],
        level=LOG_CONFIG["level"]
    )
    
    # Ensure log directory exists
    log_file = Path(LOG_CONFIG["error_log_path"])
    log_file.parent.mkdir(exist_ok=True, parents=True)
    
    # Add file handler for errors
    logger.add(
        LOG_CONFIG["error_log_path"],
        rotation=LOG_CONFIG["rotation"],
        retention=LOG_CONFIG["retention"],
        level="ERROR"
    )
    
    logger.info("Logging configured successfully")
    return logger

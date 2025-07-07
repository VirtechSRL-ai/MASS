"""
Application settings and configuration
"""
import os
from pathlib import Path
from typing import Dict, Any, List

# Project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Default configuration
DEFAULT_MAX_PAGES = int(os.getenv("MAX_PAGES", "3"))
MAX_RESULTS_PER_SOURCE = int(os.getenv("MAX_RESULTS_PER_SOURCE", "10"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Scraping configuration
SCRAPING_SOURCES = [
    {
        "name": "google",
        "enabled": True,
        "base_url": "https://www.google.com/search?q=",
        "max_results": MAX_RESULTS_PER_SOURCE
    },
    {
        "name": "duckduckgo",
        "enabled": True,
        "base_url": "https://duckduckgo.com/?q=",
        "max_results": MAX_RESULTS_PER_SOURCE
    },
    {
        "name": "firecrawl",
        "enabled": True,
        "max_results": MAX_RESULTS_PER_SOURCE
    }
]

# API settings
API_TITLE = "MASS - Multi-Agent Scraping System"
API_DESCRIPTION = "A system for web scraping and intelligent data processing with multi-agent capabilities"
API_VERSION = "1.0.0"

# Logging settings
LOG_CONFIG = {
    "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    "level": LOG_LEVEL,
    "rotation": "500 MB",
    "retention": "10 days",
    "error_log_path": str(ROOT_DIR / "logs" / "error.log")
}

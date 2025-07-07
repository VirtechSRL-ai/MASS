"""
API endpoints for the MASS system
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from datetime import datetime
from typing import Optional

from .models import ScrapingRequest, ScrapingResponse, ScrapingMetadata, ContentItem
from ..scrapers.coordinator import ScraperCoordinator
from ..agents.processor import ContentProcessor
from ..config.settings import DEFAULT_MAX_PAGES

# Create router
router = APIRouter(tags=["scrapers"])

# Initialize components
scraper_coordinator = ScraperCoordinator()
content_processor = ContentProcessor()

@router.post("/scrape", response_model=ScrapingResponse)
async def scrape_content(request: ScrapingRequest):
    """
    Scrape content based on the provided keywords and parameters
    
    This endpoint coordinates web scraping across multiple sources (min. 3),
    processes the data using AI/multi-agent systems, and returns structured results.
    """
    try:
        logger.info(f"Received scraping request for keywords: {request.keywords}")
        
        # Set default max_pages if not provided
        max_pages = request.max_pages or DEFAULT_MAX_PAGES
        
        # Perform the scraping
        scraping_result = await scraper_coordinator.scrape(
            keywords=request.keywords,
            target_domain=request.target_domain,
            max_pages=max_pages
        )
        
        # Get the raw results and metadata
        raw_results = scraping_result.get("results", [])
        metadata = scraping_result.get("metadata", {})
        
        # Process the results with AI enhancement
        enhanced_results = await content_processor.process_results(
            raw_results, 
            request.keywords
        )
        
        # Convert to ContentItem models
        content_items = [ContentItem(**item) for item in enhanced_results]
        
        # Create metadata object
        metadata_obj = ScrapingMetadata(
            keywords=request.keywords,
            target_domain=request.target_domain or "",
            scraped_at=metadata.get("scraped_at", datetime.now().isoformat()),
            total_results=len(content_items),
            sources_used=metadata.get("sources_used", []),
            execution_time=metadata.get("execution_time", 0.0)
        )
        
        # Create and return the response
        return ScrapingResponse(
            results=content_items,
            metadata=metadata_obj
        )
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns a simple status indicating the API is healthy
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

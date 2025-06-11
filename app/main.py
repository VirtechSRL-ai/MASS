from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger
import os
from typing import List, Optional
from dotenv import load_dotenv
from .scraper import MultiSourceScraper
from .config import setup_logging

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Multi-Source Scraper API")

# Setup logging
setup_logging()

class ScrapingRequest(BaseModel):
    keywords: str
    target_domain: Optional[str] = None
    max_pages: Optional[int] = 3

class ScrapingResponse(BaseModel):
    results: List[dict]
    metadata: dict

@app.post("/scrape", response_model=ScrapingResponse)
async def scrape_content(request: ScrapingRequest):
    try:
        logger.info(f"Received scraping request for keywords: {request.keywords}")
        
        scraper = MultiSourceScraper()
        results = await scraper.scrape(
            keywords=request.keywords,
            target_domain=request.target_domain,
            max_pages=request.max_pages
        )
        
        return ScrapingResponse(
            results=results,
            metadata={
                "total_results": len(results),
                "keywords": request.keywords,
                "target_domain": request.target_domain
            }
        )
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

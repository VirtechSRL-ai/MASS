"""
Scraper coordinator that manages multiple scraper implementations
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from loguru import logger

from .base import BaseScraper
from .firecrawl_scraper import FirecrawlScraper
from .playwright_scraper import PlaywrightScraper
from ..config.settings import SCRAPING_SOURCES

class ScraperCoordinator:
    """
    Coordinator that manages and orchestrates multiple scraper implementations.
    Handles the aggregation of results from different sources.
    """
    
    def __init__(self):
        """Initialize the scraper coordinator with available scrapers"""
        self.logger = logger.bind(component="ScraperCoordinator")
        self.scrapers: List[BaseScraper] = []
        
        # Initialize scrapers based on configuration
        self._initialize_scrapers()
        
    def _initialize_scrapers(self):
        """Initialize the scrapers based on configuration"""
        for source in SCRAPING_SOURCES:
            if not source.get("enabled", False):
                continue
                
            name = source["name"].lower()
            
            try:
                if name == "firecrawl":
                    self.scrapers.append(FirecrawlScraper())
                elif name in ["google", "duckduckgo"]:
                    # For search engines, use the Playwright scraper with the source name
                    self.scrapers.append(PlaywrightScraper(name=name))
                    
                self.logger.info(f"Initialized {name} scraper")
            except Exception as e:
                self.logger.error(f"Error initializing {name} scraper: {str(e)}")
        
        self.logger.info(f"Initialized {len(self.scrapers)} scrapers")
    
    async def scrape(self, 
                    keywords: str, 
                    target_domain: Optional[str] = None, 
                    max_pages: int = 3) -> Dict[str, Any]:
        """
        Coordinate scraping across multiple sources and aggregate results.
        
        Args:
            keywords: Search keywords to use
            target_domain: Optional target domain to scrape
            max_pages: Maximum number of pages to navigate through
            
        Returns:
            Dictionary containing aggregated results and metadata
        """
        start_time = time.time()
        self.logger.info(f"Starting coordinated scrape for keywords: {keywords}")
        
        # Start tasks for all scrapers
        tasks = []
        for scraper in self.scrapers:
            tasks.append(scraper.scrape(
                keywords=keywords,
                target_domain=target_domain,
                max_pages=max_pages
            ))
        
        # Wait for all scraper tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process and combine results
        combined_results = []
        sources_used = []
        seen_urls = set()  # To prevent duplicate URLs
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error from scraper {self.scrapers[i].name}: {str(result)}")
                continue
            
            # Add source name to sources used
            if result:  # Only if we got any results
                sources_used.append(self.scrapers[i].name)
            
            # Add results, avoiding duplicates by URL
            for item in result:
                if item['link'] not in seen_urls:
                    seen_urls.add(item['link'])
                    combined_results.append(item)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Create the response metadata
        metadata = {
            "keywords": keywords,
            "target_domain": target_domain if target_domain else "",
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_results": len(combined_results),
            "sources_used": sources_used,
            "execution_time": round(execution_time, 2)
        }
        
        self.logger.info(f"Completed coordinated scrape with {len(combined_results)} results in {round(execution_time, 2)}s")
        
        return {
            "results": combined_results,
            "metadata": metadata
        }

"""
Base scraper interface for all scraper implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger

class BaseScraper(ABC):
    """
    Abstract base class that defines the interface for all scrapers.
    Any scraper implementation must inherit from this class and implement the required methods.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base scraper
        
        Args:
            name: Name identifier for this scraper
        """
        self.name = name
        self.logger = logger.bind(scraper=name)
        
    @abstractmethod
    async def scrape(self, 
                     keywords: str, 
                     target_domain: Optional[str] = None, 
                     max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape content based on the given keywords and parameters.
        
        Args:
            keywords: Search keywords to use
            target_domain: Optional target domain to scrape
            max_pages: Maximum number of pages to navigate through
            
        Returns:
            List of dictionaries containing structured data from scraped content
        """
        pass
    
    def format_result(self, 
                     data: Dict[str, Any], 
                     source: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a raw scraping result into a standardized format.
        
        Args:
            data: Raw data from scraping
            source: Source of the data
            
        Returns:
            Standardized dictionary with required fields
        """
        result = {
            "title": data.get("title", "Untitled Content"),
            "link": data.get("link", ""),
            "thumbnail": data.get("thumbnail", ""),
            "source": source or self.name,
        }
        
        # Add optional fields if they exist
        optional_fields = [
            "description", "author", "published_date", 
            "duration", "views", "page_number", "metadata"
        ]
        
        for field in optional_fields:
            if field in data and data[field]:
                result[field] = data[field]
                
        return result

"""
Firecrawl-based web scraper implementation
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Union
from firecrawl import AsyncFirecrawlApp, FirecrawlApp
from loguru import logger

from .base import BaseScraper
from ..config.settings import FIRECRAWL_API_KEY

class UnsafeAsyncFirecrawlApp(AsyncFirecrawlApp):
    """
    Extended AsyncFirecrawlApp that disables SSL verification
    for compatibility with certain sites.
    """
    async def _async_request(self, method, url, headers=None, data=None, retries=3, backoff_factor=0.1):
        """
        Performs an asynchronous HTTP request with SSL verification disabled.
        
        Args:
            method: HTTP method to use
            url: URL to send the request to
            headers: Optional request headers
            data: Optional request data
            retries: Number of retries on failure
            backoff_factor: Backoff factor for retry delay
            
        Returns:
            JSON response from the request
        """
        # Create a connector that doesn't verify SSL
        connector = aiohttp.TCPConnector(ssl=False)
        
        # Use connector in the session
        async with aiohttp.ClientSession(connector=connector) as session:
            for attempt in range(retries):
                try:
                    async with session.request(
                        method, 
                        url, 
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                except Exception as e:
                    if attempt + 1 == retries:
                        raise e
                    await asyncio.sleep(backoff_factor * (2 ** attempt))


class FirecrawlScraper(BaseScraper):
    """
    Scraper implementation using Firecrawl API for both synchronous
    and asynchronous scraping capabilities.
    """
    
    def __init__(self):
        """Initialize the Firecrawl scraper with API credentials"""
        super().__init__("firecrawl")
        
        # Initialize both sync and async clients
        if not FIRECRAWL_API_KEY:
            self.logger.warning("No Firecrawl API key found. Firecrawl scraping will be disabled.")
            self.sync_client = None
            self.async_client = None
        else:
            self.sync_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
            self.async_client = UnsafeAsyncFirecrawlApp(api_key=FIRECRAWL_API_KEY)
            self.logger.info("Firecrawl clients initialized successfully")
    
    async def scrape(self, 
                    keywords: str, 
                    target_domain: Optional[str] = None, 
                    max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape content using Firecrawl based on keywords and parameters.
        
        Args:
            keywords: Search keywords to use
            target_domain: Optional target domain to scrape
            max_pages: Maximum number of pages to navigate through
            
        Returns:
            List of dictionaries containing structured data from scraped content
        """
        if not self.async_client:
            self.logger.error("Firecrawl client not initialized - cannot scrape")
            return []
        
        try:
            # If target_domain is specified, crawl it directly
            if target_domain:
                return await self._crawl_target_domain(target_domain, keywords, max_pages)
            
            # Otherwise, treat keywords as a search query and use extract endpoint
            return await self._extract_content(keywords, max_pages)
            
        except Exception as e:
            self.logger.error(f"Error during Firecrawl scraping: {str(e)}")
            return []
    
    async def _crawl_target_domain(self, 
                                  domain: str, 
                                  keywords: str, 
                                  max_pages: int) -> List[Dict[str, Any]]:
        """
        Crawls a target domain using Firecrawl.
        
        Args:
            domain: Target domain URL
            keywords: Keywords to help focus the crawl
            max_pages: Maximum pages to crawl
            
        Returns:
            List of extracted content items
        """
        self.logger.info(f"Crawling domain: {domain} with keywords: {keywords}")
        
        # Ensure the domain has a protocol
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
            
        try:
            # Execute domain crawl
            response = await self.async_client.crawl_url(
                url=domain,
                limit=max_pages * 10,  # Crawl more than we need to ensure coverage
                allow_backward_links=True,
                scrape_options={
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            )
            
            # Process crawled data into result items
            results = []
            
            # If we have crawled pages, process them
            if hasattr(response, 'pages') and response.pages:
                for i, page in enumerate(response.pages[:max_pages * 5]):  # Limit to prevent excessive processing
                    # Skip pages not relevant to our keywords if keywords provided
                    if keywords and not any(kw.lower() in str(page.content).lower() for kw in keywords.split()):
                        continue
                        
                    # Create result item from page data
                    result = {
                        "title": page.title if hasattr(page, 'title') and page.title else "Untitled Page",
                        "link": page.url if hasattr(page, 'url') and page.url else "",
                        "thumbnail": "",  # Firecrawl crawl doesn't extract thumbnails by default
                        "description": page.description if hasattr(page, 'description') and page.description else None,
                        "page_number": i + 1
                    }
                    
                    # Format and add to results
                    results.append(self.format_result(result))
                    
                    # Limit the total results
                    if len(results) >= max_pages * 3:
                        break
                        
            return results
                
        except Exception as e:
            self.logger.error(f"Error crawling domain {domain}: {str(e)}")
            return []
    
    async def _extract_content(self, query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Use Firecrawl's extract endpoint to get structured data across multiple pages.
        
        Args:
            query: The query or keywords to extract content for
            max_pages: Maximum number of pages to extract
            
        Returns:
            List of dictionaries containing structured data
        """
        self.logger.info(f"Extracting content for query: {query} across {max_pages} pages")
        
        try:
            # Use the synchronous client for extraction as it works better with the extract API
            if not self.sync_client:
                return []
                
            # Define a schema for extracting structured content
            schema = {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the content"},
                    "link": {"type": "string", "description": "URL of the content"},
                    "thumbnail": {"type": "string", "description": "URL of thumbnail image if available"},
                    "description": {"type": "string", "description": "Brief description of the content"},
                    "author": {"type": "string", "description": "Author or creator name"},
                    "published_date": {"type": "string", "description": "Publication date if available"}
                },
                "required": ["title", "link"]
            }
            
            # Define multiple search strategies to simulate pagination
            # This helps extract different results for different "pages"
            search_strategies = [
                # Page 1: Basic query
                {"prompt": f"{query}", "suffix": ""},
                # Page 2: Query with recent or trending focus
                {"prompt": f"recent {query} news and trends", "suffix": "recent"},
                # Page 3: Query with in-depth analysis focus
                {"prompt": f"detailed analysis of {query}", "suffix": "analysis"}
            ]
            
            # Additional strategies if needed
            if max_pages > 3:
                search_strategies.extend([
                    # Page 4: Query focusing on tutorials/guides
                    {"prompt": f"tutorials and guides about {query}", "suffix": "tutorials"},
                    # Page 5: Query focusing on reviews
                    {"prompt": f"reviews and opinions about {query}", "suffix": "reviews"},
                ])
            
            # Limit to requested number of pages
            search_strategies = search_strategies[:max_pages]
            
            # Process extract results into standardized format
            all_results = []
            seen_urls = set()  # Track seen URLs to avoid duplicates
            
            # Execute extraction for each search strategy (page)
            for page_num, strategy in enumerate(search_strategies, 1):
                try:
                    self.logger.info(f"Extracting page {page_num} with prompt: {strategy['prompt']}")
                    
                    # Execute extraction with this strategy
                    extract_result = self.sync_client.extract(
                        [],  # Let Firecrawl determine URLs based on the prompt
                        prompt=strategy['prompt'],
                        schema=schema,
                        agent={
                            "model": "FIRE-1"  # Use FIRE-1 model for extraction
                        }
                    )
                    
                    # Process results from this page
                    if extract_result and isinstance(extract_result, list):
                        for item in extract_result:
                            if isinstance(item, dict) and 'link' in item:
                                # Skip if we've seen this URL before
                                if item['link'] in seen_urls:
                                    continue
                                seen_urls.add(item['link'])
                                
                                # Add page number to the item
                                item['page_number'] = page_num
                                
                                # Format and add to results
                                all_results.append(self.format_result(item))
                    
                    # Brief delay between requests to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error extracting page {page_num}: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(all_results)} total results across {len(search_strategies)} pages")
            return all_results
            
        except Exception as e:
            self.logger.error(f"Error during paginated extraction for query {query}: {str(e)}")
            return []

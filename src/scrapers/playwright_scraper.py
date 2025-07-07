"""
Playwright-based web scraper implementation for dynamic websites
"""
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlparse
from playwright.async_api import async_playwright
from loguru import logger

from .base import BaseScraper

class PlaywrightScraper(BaseScraper):
    """
    Scraper implementation using Playwright for browser automation
    to handle dynamic websites, JavaScript rendering, and pagination.
    """
    
    def __init__(self, name: str = "playwright"):
        """Initialize the Playwright scraper"""
        super().__init__(name)
        
        # Define selectors for common content types and sites
        self.selectors = {
            'generic': {
                'links': 'a[href]',
                'next_page': 'a:has-text("Next"), a.next, a.pagination-next, a[rel="next"]',
                'load_more': 'button:has-text("Load more"), button:has-text("Show more")'
            },
            'google': {
                'result_container': '#search',
                'result_items': '.g',
                'title': 'h3',
                'link': 'a[href]',
                'description': '.VwiC3b',
                'next_page': '#pnnext'
            },
            'duckduckgo': {
                'result_container': '.results',
                'result_items': '.result',
                'title': '.result__title',
                'link': '.result__title a[href]',
                'description': '.result__snippet',
                'next_page': '.result--more'
            }
        }
    
    async def scrape(self, 
                    keywords: str, 
                    target_domain: Optional[str] = None, 
                    max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape content using Playwright based on the given keywords and parameters.
        
        Args:
            keywords: Search keywords to use
            target_domain: Optional target domain to scrape
            max_pages: Maximum number of pages to navigate through
            
        Returns:
            List of dictionaries containing structured data from scraped content
        """
        self.logger.info(f"Starting Playwright scraping for: {keywords}")
        
        results = []
        
        # Determine the target URL
        url = self._build_target_url(keywords, target_domain)
        
        try:
            async with async_playwright() as p:
                # Launch browser with stealth options
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                
                # Set up a new page with timeout
                page = await context.new_page()
                
                # Navigate to the target URL
                await page.goto(url, timeout=30000)
                self.logger.info(f"Navigated to {url}")
                
                # Extract data from the current page and subsequent pages
                for page_num in range(1, max_pages + 1):
                    self.logger.info(f"Scraping page {page_num} of {max_pages}")
                    
                    # Wait for the page to load properly
                    await asyncio.sleep(2)
                    
                    # Extract data from the current page
                    page_results = await self._extract_page_data(page, page_num, target_domain)
                    results.extend(page_results)
                    
                    # Check if we've reached the maximum pages
                    if page_num >= max_pages:
                        break
                    
                    # Try to navigate to the next page
                    has_next = await self._navigate_to_next_page(page)
                    if not has_next:
                        self.logger.info("No more pages available")
                        break
                
                await browser.close()
                
            return results
        except Exception as e:
            self.logger.error(f"Error during Playwright scraping: {str(e)}")
            return []
    
    def _build_target_url(self, keywords: str, target_domain: Optional[str] = None) -> str:
        """
        Build the target URL for scraping.
        
        Args:
            keywords: Search keywords
            target_domain: Optional target domain
            
        Returns:
            Complete URL to navigate to
        """
        if target_domain:
            # If a specific domain is provided, navigate to it directly
            if not target_domain.startswith(('http://', 'https://')):
                return f"https://{target_domain}"
            return target_domain
        
        # Default to Google search
        return f"https://www.google.com/search?q={quote(keywords)}"
    
    async def _extract_page_data(self, 
                               page, 
                               page_num: int, 
                               target_domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract data from the current page.
        
        Args:
            page: Playwright page object
            page_num: Current page number
            target_domain: Optional target domain
            
        Returns:
            List of extracted data items
        """
        results = []
        
        try:
            # Determine which selectors to use based on the URL
            domain = urlparse(page.url).netloc
            selector_key = 'generic'
            
            if 'google.com' in domain:
                selector_key = 'google'
            elif 'duckduckgo.com' in domain:
                selector_key = 'duckduckgo'
            
            selectors = self.selectors[selector_key]
            
            # Wait for content to load
            if 'result_container' in selectors:
                await page.wait_for_selector(selectors['result_container'], timeout=10000)
            
            # For generic sites, extract all links and their text
            if selector_key == 'generic':
                links = await page.query_selector_all(selectors['links'])
                
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        if not href or href.startswith('#') or href.startswith('javascript'):
                            continue
                            
                        # Make relative URLs absolute
                        if href.startswith('/'):
                            base_url = f"{page.url.split('/')[0]}//{page.url.split('/')[2]}"
                            href = f"{base_url}{href}"
                            
                        # Get link text as title
                        title = await link.text_content()
                        title = title.strip() if title else "No title"
                        
                        # Create result item
                        result = {
                            "title": title,
                            "link": href,
                            "thumbnail": "",
                            "page_number": page_num,
                            "description": ""
                        }
                        
                        # Format and add to results if relevant
                        if target_domain and target_domain not in href:
                            continue
                            
                        results.append(self.format_result(result))
                    except Exception as e:
                        self.logger.debug(f"Error processing link: {str(e)}")
                        continue
            
            # For specific search engines, use their result structures
            else:
                result_items = await page.query_selector_all(selectors['result_items'])
                
                for item in result_items:
                    try:
                        # Extract title element
                        title_elem = await item.query_selector(selectors['title'])
                        title = await title_elem.text_content() if title_elem else "No title"
                        
                        # Extract link
                        link_elem = await item.query_selector(selectors['link'])
                        link = await link_elem.get_attribute('href') if link_elem else ""
                        
                        # Extract description
                        desc_elem = await item.query_selector(selectors['description'])
                        description = await desc_elem.text_content() if desc_elem else ""
                        
                        # Create result item
                        result = {
                            "title": title.strip(),
                            "link": link,
                            "thumbnail": "",
                            "page_number": page_num,
                            "description": description.strip()
                        }
                        
                        # Format and add to results if relevant
                        if target_domain and target_domain not in link:
                            continue
                            
                        results.append(self.format_result(result))
                    except Exception as e:
                        self.logger.debug(f"Error processing result item: {str(e)}")
                        continue
            
            self.logger.info(f"Extracted {len(results)} items from page {page_num}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error extracting data from page: {str(e)}")
            return []
    
    async def _navigate_to_next_page(self, page) -> bool:
        """
        Attempt to navigate to the next page of results.
        
        Args:
            page: Playwright page object
            
        Returns:
            Boolean indicating if navigation was successful
        """
        # Determine which selectors to use based on the URL
        domain = urlparse(page.url).netloc
        selector_key = 'generic'
        
        if 'google.com' in domain:
            selector_key = 'google'
        elif 'duckduckgo.com' in domain:
            selector_key = 'duckduckgo'
        
        selectors = self.selectors[selector_key]
        
        try:
            # Look for a next page link
            next_button = await page.query_selector(selectors['next_page'])
            
            if next_button:
                # Click the next button and wait for navigation
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                return True
            
            # If there's a "load more" button for infinite scroll sites
            if 'load_more' in selectors:
                load_more = await page.query_selector(selectors['load_more'])
                if load_more:
                    await load_more.click()
                    await page.wait_for_load_state('networkidle')
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"No next page available: {str(e)}")
            return False

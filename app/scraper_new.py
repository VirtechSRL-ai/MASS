import asyncio
import os
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote
from playwright.async_api import async_playwright
from loguru import logger
from app.config import SCRAPING_SOURCES
from firecrawl import FirecrawlApp

class MultiSourceScraper:
    def __init__(self):
        firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        if not firecrawl_api_key or firecrawl_api_key == 'your_firecrawl_api_key_here':
            logger.warning("No valid Firecrawl API key found. Firecrawl scraping will be disabled.")
            self.firecrawl = None
        else:
            try:
                self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
                logger.info("Initialized FirecrawlApp")
            except Exception as e:
                logger.error(f"Error initializing FirecrawlApp: {str(e)}")
                self.firecrawl = None

    def _scrape_with_firecrawl_url(self, url: str) -> Union[List[Dict], Exception]:
        """Use Firecrawl to scrape a specific URL with advanced agent-based navigation"""
        try:
            logger.info(f"Starting Firecrawl scrape for URL: {url}")
            result = self.firecrawl.scrape_url(
                url,
                formats=["markdown", "html"],
                agent={
                    "model": "FIRE-1",
                    "prompt": (
                        "Click any 'Accept' or 'I am over 18' buttons if they appear. "
                        "Then navigate through paginated results by clicking the 'Next' button until it's disabled. "
                        "Scrape each page for content titles, thumbnails, links, and any metadata like dates or descriptions."
                    )
                }
            )
            
            # Format the result to match our expected schema
            formatted_results = []
            if isinstance(result, dict):
                if 'content' in result:
                    # Parse and format the scraped content
                    formatted_results.append({
                        'title': result.get('title', url),
                        'link': url,
                        'snippet': result.get('content', {}).get('markdown', '')[:200] + '...' if result.get('content', {}).get('markdown') else '',
                        'source': 'firecrawl',
                        'page_number': 1,
                        'metadata': {
                            'timestamp': result.get('timestamp'),
                            'scraped_at': result.get('scraped_at'),
                            'format_types': result.get('content', {}).keys()
                        }
                    })
                elif 'results' in result and isinstance(result['results'], list):
                    for i, item in enumerate(result['results']):
                        formatted_results.append({
                            'title': item.get('title', f"Result {i+1}"),
                            'link': item.get('url', item.get('link', url)),
                            'snippet': item.get('content', item.get('description', ''))[:200] + '...' if item.get('content', item.get('description', '')) else '',
                            'source': 'firecrawl',
                            'page_number': item.get('page_number', 1),
                            'metadata': {
                                'thumbnail': item.get('thumbnail'),
                                'duration': item.get('duration'),
                                'timestamp': item.get('timestamp')
                            }
                        })
            
            logger.info(f"Firecrawl scrape for {url} completed with {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error with Firecrawl scrape_url: {str(e)}")
            return e
            
    async def _scrape_with_playwright(self, url: str, max_pages: int = 3) -> List[Dict]:
        results = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                page = await context.new_page()
                
                try:
                    # Configure browser for stealth
                    await page.set_extra_http_headers({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9'
                    })
                    
                    # Set geolocation to US
                    await context.grant_permissions(['geolocation'])
                    await context.set_geolocation({'latitude': 37.7749, 'longitude': -122.4194})
                    
                    # Navigate to URL
                    await page.goto(url)
                    await page.wait_for_load_state('networkidle')
                    
                    # Handle Google cookie consent
                    try:
                        consent_frame = await page.wait_for_selector('iframe[src*="consent.google.com"]', timeout=10000)
                        if consent_frame:
                            frame = await consent_frame.content_frame()
                            accept_button = await frame.wait_for_selector('button:has-text("Accept all")', timeout=10000)
                            if accept_button:
                                await accept_button.click()
                                await page.wait_for_load_state('networkidle')
                                logger.info("Accepted cookie consent")
                    except Exception as e:
                        logger.info(f"No cookie consent found: {str(e)}")
                        
                    # Process each page
                    for page_num in range(max_pages):
                        try:
                            logger.info(f"Scraping page {page_num + 1} of {max_pages}")
                            
                            # Wait for Google results
                            await page.wait_for_selector('div[data-snf]', timeout=10000)
                            elements = await page.query_selector_all('div[data-snf]')
                            
                            if not elements:
                                logger.error("No search results found on page")
                                break
                                
                            # Extract data from each result
                            for element in elements:
                                try:
                                    title_el = await element.query_selector('h3')
                                    link_el = await element.query_selector('a')
                                    snippet_el = await element.query_selector('div.VwiC3b')
                                    
                                    if title_el and link_el:
                                        title = await title_el.inner_text()
                                        link = await link_el.get_attribute('href')
                                        snippet = await snippet_el.inner_text() if snippet_el else ''
                                        
                                        if title and link:
                                            results.append({
                                                'title': title,
                                                'link': link,
                                                'snippet': snippet,
                                                'source': 'google',
                                                'page_number': page_num + 1
                                            })
                                except Exception as e:
                                    logger.error(f"Error extracting result: {str(e)}")
                                    continue
                                    
                            # Try to navigate to next page
                            if page_num < max_pages - 1:
                                try:
                                    # Try multiple selectors for next page button
                                    next_selectors = ['#pnnext', 'a[aria-label="Next page"]', 'a.nBDE1b']
                                    next_button = None
                                    
                                    for selector in next_selectors:
                                        try:
                                            next_button = await page.wait_for_selector(selector, timeout=2000)
                                            if next_button:
                                                # Ensure the button is clickable
                                                await next_button.scroll_into_view_if_needed()
                                                await page.wait_for_timeout(1000)
                                                await next_button.click()
                                                await page.wait_for_load_state('networkidle')
                                                await page.wait_for_timeout(2000)
                                                break
                                        except Exception:
                                            continue
                                            
                                    if not next_button:
                                        logger.info("No next page button found")
                                        break
                                except Exception as e:
                                    logger.error(f"Error navigating to next page: {str(e)}")
                                    break
                        except Exception as e:
                            logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                            break
                except Exception as e:
                    logger.error(f"Error during scraping: {str(e)}")
                finally:
                    await browser.close()
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            
        return results

    async def scrape(self, keywords: str, target_domain: Optional[str] = None, max_pages: int = 3) -> List[Dict]:
        tasks = []
        
        for source in SCRAPING_SOURCES:
            if not source['enabled']:
                continue
                
            if source['name'] == 'google':
                if target_domain:
                    logger.info(f"Scraping target domain directly: {target_domain}")
                    tasks.append(self._scrape_with_playwright(target_domain, max_pages))
                else:
                    encoded_query = quote(keywords)
                    url = f"https://www.google.com/search?q={encoded_query}&num=30"
                    logger.info(f"Searching Google with URL: {url}")
                    tasks.append(self._scrape_with_playwright(url, max_pages))
            elif source['name'] == 'firecrawl' and self.firecrawl is not None:
                # Determine which method to use based on whether we have a target domain
                if target_domain:
                    logger.info(f"Using Firecrawl to scrape specific URL: {target_domain}")
                    tasks.append(self._scrape_with_firecrawl_url(target_domain))
                else:
                    logger.info(f"Searching Firecrawl with keywords: {keywords}")
                    tasks.append(self.firecrawl.search(keywords))
            
        if not tasks:
            logger.warning("No enabled scraping sources found")
            return []
            
        logger.info(f"Starting concurrent scraping with {len(tasks)} tasks")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and handle exceptions
        all_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed: {str(result)}")
            elif isinstance(result, list):
                all_results.extend(result)
                
        # Filter by domain if specified
        if target_domain:
            all_results = [r for r in all_results if target_domain in r.get('link', '')]
            
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get('link')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                
        # Sort by page number and limit to top results
        unique_results.sort(key=lambda x: (x.get('page_number', 1), x.get('title', '')))
        return unique_results[:50]  # Return top 50 results

from playwright.async_api import async_playwright
from firecrawl import FirecrawlApp
from loguru import logger
from typing import List, Optional, Dict
import asyncio
from .config import SCRAPING_SOURCES

class MultiSourceScraper:
    def __init__(self):
        pass  # No initialization needed for now

    async def _scrape_with_playwright(self, url: str, max_pages: int = 3) -> List[Dict]:
        """Scrape content using Playwright."""
        results = []
        async with async_playwright() as p:
            logger.info(f"Starting Playwright scraping for URL: {url}")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                logger.info(f"Navigating to URL: {url}")
                await page.goto(url, wait_until='networkidle')
                for page_num in range(max_pages):
                    logger.info(f"Scraping page {page_num + 1} of {max_pages}")
                    # Extract content from current page
                    # Wait for search results to load
                    await page.wait_for_selector('.b_algo', timeout=5000)
                    
                    items = await page.evaluate(f"""
                        (page_number) => {{
                            const results = [];
                            // Bing specific selectors
                            const items = document.querySelectorAll('.b_algo');
                            
                            items.forEach(item => {{
                                const titleEl = item.querySelector('h2');
                                const linkEl = titleEl ? titleEl.querySelector('a') : null;
                                const descEl = item.querySelector('.b_caption p');
                                const imgEl = item.querySelector('.cico img');
                                
                                if (titleEl && linkEl && linkEl.href) {{
                                    results.push({{
                                        title: titleEl.textContent.trim(),
                                        link: linkEl.href,
                                        description: descEl ? descEl.textContent.trim() : '',
                                        thumbnail: imgEl ? imgEl.src : '',
                                        source: window.location.hostname,
                                        page_number: page_number
                                    }});
                                }}
                            }});
                            return results;
                        }}
                    """, page_num + 1)
                    
                    logger.info(f"Found {len(items)} results on page {page_num + 1}")
                    results.extend(items)
                    
                    if page_num < max_pages - 1:  # Don't try to navigate on the last page
                        # Try to find Bing's next page button
                        next_button = await page.query_selector('.b_pag li.b_adv a')
                        
                        if next_button:
                            logger.info("Found next page button, navigating...")
                            await next_button.click()
                            await page.wait_for_load_state('networkidle')
                            await page.wait_for_selector('.b_algo', timeout=5000)
                            # Give a short pause to ensure content is loaded
                            await page.wait_for_timeout(1000)
                        else:
                            logger.info("No next page button found, stopping pagination")
                            break
                    
            except Exception as e:
                logger.error(f"Error during Playwright scraping: {str(e)}")
            finally:
                await browser.close()
                
        return results

    async def _scrape_with_firecrawl(self, url: str) -> List[Dict]:
        """Scrape content using Firecrawl."""
        try:
            result = await self.firecrawl.scrape_url(url, formats=['markdown'])
            # Transform Firecrawl result into our standard format
            return [{
                'title': item.get('title', ''),
                'link': item.get('url', ''),
                'thumbnail': item.get('image', ''),
                'source': 'firecrawl',
                'content': item.get('content', ''),
                'page_number': 1
            } for item in result.get('items', [])]
        except Exception as e:
            logger.error(f"Error during Firecrawl scraping: {str(e)}")
            return []

    async def scrape(self, keywords: str, target_domain: Optional[str] = None, max_pages: int = 3) -> List[Dict]:
        """Main scraping method that coordinates different scraping sources."""
        all_results = []
        tasks = []

        for source in SCRAPING_SOURCES:
            if not source['enabled']:
                continue

            if source['name'] == 'bing':
                # For Bing, we need to construct the URL carefully
                from urllib.parse import quote
                query = keywords
                if target_domain:
                    query = f"{keywords} site:{target_domain}"
                
                encoded_query = quote(query)
                url = f"https://www.bing.com/search?q={encoded_query}&form=QBLH"
                
                logger.info(f"Searching Bing with URL: {url}")
                tasks.append(self._scrape_with_playwright(url, max_pages))

        # Run all scraping tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and filter results
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)

        # Deduplicate results based on URL
        seen_urls = set()
        unique_results = []
        for item in all_results:
            if item['link'] not in seen_urls:
                seen_urls.add(item['link'])
                unique_results.append(item)

        return unique_results[:50]  # Limit to top 50 results

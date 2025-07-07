"""
Unit tests for the scrapers
"""
import unittest
from unittest.mock import patch, MagicMock
import asyncio
import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.scrapers.base import BaseScraper
from src.scrapers.firecrawl_scraper import FirecrawlScraper
from src.scrapers.playwright_scraper import PlaywrightScraper
from src.api.models import ScrapingRequest


class TestBaseScraper(unittest.TestCase):
    """Tests for the BaseScraper class"""
    
    def test_abstract_methods(self):
        """Test that BaseScraper cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseScraper()
    
    def test_format_results(self):
        """Test the format_results method"""
        class DummyScraper(BaseScraper):
            async def scrape(self, request):
                pass
        
        scraper = DummyScraper()
        raw_results = [
            {"title": "Test Title 1", "link": "http://example.com/1"},
            {"title": "Test Title 2", "link": "http://example.com/2", "thumbnail": "image.jpg"}
        ]
        
        formatted = scraper.format_results(raw_results)
        
        # Check that source field was added
        for result in formatted:
            self.assertIn("source", result)
            self.assertEqual(result["source"], "dummy")
        
        # Check that original data was preserved
        self.assertEqual(formatted[0]["title"], "Test Title 1")
        self.assertEqual(formatted[0]["link"], "http://example.com/1")
        self.assertEqual(formatted[1]["thumbnail"], "image.jpg")


class TestFirecrawlScraper(unittest.TestCase):
    """Tests for the FirecrawlScraper class"""
    
    @patch('src.scrapers.firecrawl_scraper.FirecrawlApp')
    @patch('src.scrapers.firecrawl_scraper.AsyncFirecrawlApp')
    def test_initialization(self, mock_async_client, mock_sync_client):
        """Test the initialization of FirecrawlScraper"""
        # Mock API key
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_key"}):
            scraper = FirecrawlScraper()
            self.assertIsNotNone(scraper)
            mock_sync_client.assert_called_once_with("test_key")
            mock_async_client.assert_called_once_with("test_key")
    
    @patch('src.scrapers.firecrawl_scraper.FirecrawlScraper._extract_data')
    @patch('src.scrapers.firecrawl_scraper.FirecrawlScraper._crawl')
    def test_scrape(self, mock_crawl, mock_extract):
        """Test the scrape method"""
        # Setup mocks
        mock_crawl.return_value = asyncio.Future()
        mock_crawl.return_value.set_result(["http://example.com"])
        
        mock_extract.return_value = asyncio.Future()
        mock_extract.return_value.set_result([
            {"title": "Test Title", "link": "http://example.com"}
        ])
        
        # Create scraper with mocked clients
        scraper = FirecrawlScraper()
        scraper._async_client = MagicMock()
        scraper._sync_client = MagicMock()
        
        # Create request
        request = ScrapingRequest(
            keywords="test query",
            max_pages=1
        )
        
        # Run the test
        results = asyncio.run(scraper.scrape(request))
        
        # Verify the results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Title")
        self.assertEqual(results[0]["link"], "http://example.com")
        self.assertEqual(results[0]["source"], "firecrawl")


class TestPlaywrightScraper(unittest.TestCase):
    """Tests for the PlaywrightScraper class"""
    
    @patch('src.scrapers.playwright_scraper.async_playwright')
    def test_initialization(self, mock_playwright):
        """Test the initialization of PlaywrightScraper"""
        scraper = PlaywrightScraper()
        self.assertIsNotNone(scraper)
    
    @patch('src.scrapers.playwright_scraper.PlaywrightScraper._setup_browser')
    @patch('src.scrapers.playwright_scraper.PlaywrightScraper._navigate_to_search')
    @patch('src.scrapers.playwright_scraper.PlaywrightScraper._extract_search_results')
    async def test_scrape_async(self, mock_extract, mock_navigate, mock_setup):
        """Test the scrape method"""
        # Setup mocks
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_setup.return_value = (mock_browser, mock_page)
        
        mock_extract.return_value = [
            {"title": "Test Result", "link": "http://example.com"}
        ]
        
        # Create scraper
        scraper = PlaywrightScraper()
        
        # Create request
        request = ScrapingRequest(
            keywords="test search",
            max_pages=1
        )
        
        # Run the test
        results = []
        async def run_test():
            nonlocal results
            results = await scraper.scrape(request)
        
        # We need to use unittest's loop to run the coroutine
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
        
        # Check results format
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Result")
        self.assertEqual(results[0]["source"], "playwright")


if __name__ == "__main__":
    unittest.main()

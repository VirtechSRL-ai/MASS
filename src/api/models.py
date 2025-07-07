"""
Data models for the API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ScrapingRequest(BaseModel):
    """Request model for scraping content"""
    keywords: str = Field(..., description="Search keywords or query")
    target_domain: Optional[str] = Field(None, description="Optional target domain to scrape")
    max_pages: Optional[int] = Field(3, description="Maximum number of pages to scrape")

class ContentItem(BaseModel):
    """Model for a single content item from scraping results"""
    title: str = Field(..., description="The title of the content")
    link: str = Field(..., description="URL of the content")
    thumbnail: str = Field("", description="URL of thumbnail image if available")
    source: Optional[str] = Field(None, description="Source where the content was scraped from")
    description: Optional[str] = Field(None, description="Brief description or summary")
    author: Optional[str] = Field(None, description="Author or creator of the content")
    published_date: Optional[str] = Field(None, description="Publication date if available")
    duration: Optional[str] = Field(None, description="Duration (for video/audio content)")
    views: Optional[str] = Field(None, description="View count if available")
    page_number: Optional[int] = Field(None, description="Page number where item was found")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class ScrapingMetadata(BaseModel):
    """Metadata for scraping results"""
    keywords: str = Field(..., description="Keywords used for the search")
    target_domain: str = Field("", description="Target domain that was scraped, if specified")
    scraped_at: str = Field(..., description="Timestamp when the scraping was performed")
    total_results: int = Field(..., description="Total number of results found")
    sources_used: List[str] = Field(default_factory=list, description="List of sources that were used")
    execution_time: float = Field(0.0, description="Time taken to execute the scraping in seconds")

class ScrapingResponse(BaseModel):
    """Response model for scraping results"""
    results: List[ContentItem] = Field(..., description="List of scraped content items")
    metadata: ScrapingMetadata = Field(..., description="Metadata about the scraping operation")

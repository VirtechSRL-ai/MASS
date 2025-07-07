"""
Helper utilities for the MASS system
"""
import re
from urllib.parse import urlparse, urljoin, quote
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import hashlib
from loguru import logger

def normalize_url(url: str) -> str:
    """
    Normalize a URL by ensuring it has a proper scheme and formatting.
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL
    """
    # Add https:// if no scheme is present
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
        
    # Remove trailing slash if present
    if url.endswith('/'):
        url = url[:-1]
        
    return url

def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        parsed = urlparse(normalize_url(url))
        return parsed.netloc
    except Exception:
        return ""

def build_search_url(base_url: str, query: str) -> str:
    """
    Build a search URL by combining a base URL with a query.
    
    Args:
        base_url: The base search URL
        query: Search query to append
        
    Returns:
        Complete search URL
    """
    # Encode the query for URL
    encoded_query = quote(query)
    
    # Handle different search engine formats
    if "google.com" in base_url:
        return f"{base_url}{encoded_query}"
    elif "duckduckgo.com" in base_url:
        return f"{base_url}{encoded_query}"
    else:
        # Generic handling
        if "?" in base_url:
            return f"{base_url}&q={encoded_query}"
        else:
            return f"{base_url}?q={encoded_query}"

def create_content_hash(content: Dict[str, Any]) -> str:
    """
    Create a unique hash from content to identify duplicates.
    
    Args:
        content: Content dictionary to hash
        
    Returns:
        Hash string
    """
    # Use URL as the primary key for deduplication
    if "link" in content and content["link"]:
        return hashlib.md5(content["link"].encode()).hexdigest()
    
    # If no URL, use title and description
    hash_input = (
        content.get("title", "") + 
        content.get("description", "") + 
        content.get("author", "")
    )
    
    return hashlib.md5(hash_input.encode()).hexdigest()

def serialize_datetime(obj: Any) -> Any:
    """
    Serialize datetime objects to ISO format for JSON serialization.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serialized object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def safe_json_dumps(data: Any) -> str:
    """
    Safely convert data to JSON string with custom serializers.
    
    Args:
        data: Data to convert to JSON
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(data, default=serialize_datetime, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error serializing data to JSON: {str(e)}")
        # Attempt to create a serializable version
        if isinstance(data, dict):
            clean_data = {k: str(v) for k, v in data.items()}
            return json.dumps(clean_data, ensure_ascii=False)
        return json.dumps(str(data), ensure_ascii=False)

def extract_metadata_from_html(html_content: str) -> Dict[str, Any]:
    """
    Extract metadata from HTML content.
    
    Args:
        html_content: HTML content string
        
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {}
    
    # Extract title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        metadata['title'] = title_match.group(1).strip()
    
    # Extract meta description
    desc_match = re.search(r'<meta[^>]*name=["|\']description["|\'][^>]*content=["|\']([^"|\']*)["|\']', 
                          html_content, re.IGNORECASE)
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()
    
    # Extract meta keywords
    kw_match = re.search(r'<meta[^>]*name=["|\']keywords["|\'][^>]*content=["|\']([^"|\']*)["|\']', 
                        html_content, re.IGNORECASE)
    if kw_match:
        metadata['keywords'] = kw_match.group(1).strip()
    
    # Extract og:image (thumbnail)
    img_match = re.search(r'<meta[^>]*property=["|\']og:image["|\'][^>]*content=["|\']([^"|\']*)["|\']', 
                         html_content, re.IGNORECASE)
    if img_match:
        metadata['thumbnail'] = img_match.group(1).strip()
    
    # Extract author
    author_match = re.search(r'<meta[^>]*name=["|\']author["|\'][^>]*content=["|\']([^"|\']*)["|\']', 
                            html_content, re.IGNORECASE)
    if author_match:
        metadata['author'] = author_match.group(1).strip()
    
    return metadata

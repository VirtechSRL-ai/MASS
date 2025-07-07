"""
AI-based content processor for enhancing and analyzing scraped data
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

# Check if OpenAI is available, otherwise use a dummy implementation
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from ..config.settings import OPENAI_API_KEY

class ContentProcessor:
    """
    AI-based processor that enhances scraped content with additional
    intelligence, categorization, and analysis.
    """
    
    def __init__(self):
        """Initialize the content processor"""
        self.logger = logger.bind(component="ContentProcessor")
        
        # Initialize AI client if available
        if HAS_OPENAI and OPENAI_API_KEY:
            try:
                # Initialize with just the API key, avoiding proxies or other problematic parameters
                self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                self.logger.info("Initialized OpenAI client for content processing")
            except Exception as e:
                self.client = None
                self.logger.error(f"Failed to initialize OpenAI client: {str(e)} - using dummy processing")
        else:
            self.client = None
            self.logger.warning("OpenAI client not available - using dummy processing")
    
    async def process_results(self, results: List[Dict[str, Any]], keywords: str) -> List[Dict[str, Any]]:
        """
        Process scraped results to add intelligence and enhanced metadata.
        
        Args:
            results: List of scraped content items
            keywords: Original search keywords
            
        Returns:
            Enhanced list of content items
        """
        if not results:
            return results
            
        self.logger.info(f"Processing {len(results)} results with AI enhancement")
        
        # If OpenAI is available, use it for processing
        if self.client:
            return await self._process_with_openai(results, keywords)
        
        # Otherwise use dummy processing
        return await self._process_with_dummy(results, keywords)
    
    async def _process_with_openai(self, results: List[Dict[str, Any]], keywords: str) -> List[Dict[str, Any]]:
        """
        Process results using OpenAI for enhanced metadata and analysis.
        
        Args:
            results: List of scraped content items
            keywords: Original search keywords
            
        Returns:
            Enhanced list of content items
        """
        enhanced_results = []
        
        # Process in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            
            # Process each item in the batch concurrently
            tasks = []
            for item in batch:
                tasks.append(self._enhance_item_with_openai(item, keywords))
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing item {i+j}: {str(result)}")
                    enhanced_results.append(batch[j])
                else:
                    enhanced_results.append(result)
        
        self.logger.info(f"Enhanced {len(enhanced_results)} results with OpenAI")
        return enhanced_results
    
    async def _enhance_item_with_openai(self, item: Dict[str, Any], keywords: str) -> Dict[str, Any]:
        """
        Enhance a single content item with OpenAI.
        
        Args:
            item: Content item to enhance
            keywords: Original search keywords
            
        Returns:
            Enhanced content item
        """
        try:
            # Extract the existing information
            title = item.get('title', '')
            description = item.get('description', '')
            
            # Skip if not enough content to process
            if len(title) < 3:
                return item
                
            # Create a prompt for OpenAI
            content = f"Title: {title}\n"
            if description:
                content += f"Description: {description}\n"
                
            prompt = f"""Analyze this content related to the search query "{keywords}":
            
            {content}
            
            Provide a JSON response with these fields:
            1. relevance_score (0-100): How relevant this content is to the query
            2. content_type: The likely type (article, video, product, etc.)
            3. enhanced_description: A better description if the original is missing or poor
            4. tags: Up to 5 relevant tags or keywords
            
            JSON format only."""
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes web content and provides structured data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.2
            )
            
            # Extract and parse the response
            if response.choices and response.choices[0].message:
                response_text = response.choices[0].message.content.strip()
                
                # Extract JSON from the response
                try:
                    # Find JSON content between triple backticks if present
                    if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
                        json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in response_text and "```" in response_text.split("```", 1)[1]:
                        json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                    else:
                        json_str = response_text
                        
                    ai_analysis = json.loads(json_str)
                    
                    # Update the item with the AI analysis
                    if 'metadata' not in item:
                        item['metadata'] = {}
                        
                    item['metadata']['ai_analysis'] = {
                        'relevance_score': ai_analysis.get('relevance_score', 0),
                        'content_type': ai_analysis.get('content_type', 'unknown'),
                        'tags': ai_analysis.get('tags', [])
                    }
                    
                    # Update description if enhanced one is available
                    if not item.get('description') and ai_analysis.get('enhanced_description'):
                        item['description'] = ai_analysis.get('enhanced_description')
                    
                except Exception as e:
                    self.logger.error(f"Error parsing OpenAI response: {str(e)}")
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error with OpenAI enhancement: {str(e)}")
            return item
    
    async def _process_with_dummy(self, results: List[Dict[str, Any]], keywords: str) -> List[Dict[str, Any]]:
        """
        Process results with a dummy implementation when OpenAI is not available.
        
        Args:
            results: List of scraped content items
            keywords: Original search keywords
            
        Returns:
            List of content items with basic enhancements
        """
        self.logger.info("Using dummy processor to enhance results")
        
        # Extract keywords for basic tagging
        tags = [kw.strip().lower() for kw in keywords.split() if len(kw.strip()) > 2]
        
        for item in results:
            # Add basic metadata
            if 'metadata' not in item:
                item['metadata'] = {}
                
            item['metadata']['processed'] = True
            
            # Add simple content type classification based on URL
            url = item.get('link', '').lower()
            
            if 'youtube' in url:
                content_type = 'video'
            elif 'wikipedia' in url:
                content_type = 'article'
            elif any(ext in url for ext in ['.jpg', '.png', '.gif']):
                content_type = 'image'
            elif any(ext in url for ext in ['.pdf', '.doc']):
                content_type = 'document'
            else:
                content_type = 'webpage'
                
            # Add simple relevance score based on keyword presence
            title = item.get('title', '').lower()
            description = item.get('description', '').lower()
            
            # Count keyword occurrences for relevance
            keyword_count = 0
            for tag in tags:
                keyword_count += title.count(tag)
                keyword_count += description.count(tag)
                
            relevance_score = min(100, keyword_count * 10)
            
            # Add the analysis metadata
            item['metadata']['ai_analysis'] = {
                'relevance_score': relevance_score,
                'content_type': content_type,
                'tags': tags[:5]  # Limit to 5 tags
            }
        
        return results

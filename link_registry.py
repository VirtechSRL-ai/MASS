"""
Link Registry Module

This module provides functionality to track and manage links across different scripts
to prevent duplicate links from being returned by multiple scripts.
"""
import os
import json
from pathlib import Path
import datetime

class LinkRegistry:
    """
    A class to manage a registry of links that have been processed by various scripts.
    This helps prevent duplicate links from being returned by different scripts.
    """
    
    def __init__(self, registry_file=None):
        """
        Initialize the LinkRegistry with an optional registry file path.
        
        Args:
            registry_file (str, optional): Path to the registry file. If None, uses default location.
        """
        if registry_file is None:
            # Default location in the same directory as this script
            self.registry_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "outputs", 
                "link_registry.json"
            )
        else:
            self.registry_file = registry_file
            
        # Create outputs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        
        # Load existing registry or create a new one
        self.links = self._load_registry()
    
    def _load_registry(self):
        """Load the link registry from file or create a new one if it doesn't exist."""
        try:
            if os.path.exists(self.registry_file):
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "links": {},  # URL -> {"script": script_name, "timestamp": timestamp}
                    "metadata": {
                        "created": datetime.datetime.now().isoformat(),
                        "last_updated": datetime.datetime.now().isoformat()
                    }
                }
        except Exception as e:
            print(f"Error loading registry: {e}")
            # Return a new registry if there's an error
            return {
                "links": {},
                "metadata": {
                    "created": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "error": str(e)
                }
            }
    
    def _save_registry(self):
        """Save the link registry to file."""
        try:
            # Update the last_updated timestamp
            self.links["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.links, f, indent=2)
        except Exception as e:
            print(f"Error saving registry: {e}")
    
    def register_links(self, urls, script_name):
        """
        Register a list of URLs as being processed by a script.
        
        Args:
            urls (list): List of URLs to register
            script_name (str): Name of the script that processed these URLs
            
        Returns:
            int: Number of new URLs registered
        """
        if not urls:
            return 0
            
        new_count = 0
        timestamp = datetime.datetime.now().isoformat()
        
        for url in urls:
            if url and url not in self.links["links"]:
                self.links["links"][url] = {
                    "script": script_name,
                    "timestamp": timestamp
                }
                new_count += 1
        
        # Save the updated registry
        self._save_registry()
        return new_count
    
    def filter_new_links(self, urls, script_name=None):
        """
        Filter a list of URLs to only include those not already in the registry.
        
        Args:
            urls (list): List of URLs to filter
            script_name (str, optional): If provided, also include URLs previously registered by this script
            
        Returns:
            list: Filtered list of URLs not in the registry (or from the same script)
        """
        if not urls:
            return []
            
        filtered_urls = []
        
        for url in urls:
            if not url:
                continue
                
            if url not in self.links["links"]:
                filtered_urls.append(url)
            elif script_name and self.links["links"][url]["script"] == script_name:
                # Include URLs previously registered by the same script
                filtered_urls.append(url)
                
        return filtered_urls
    
    def get_stats(self):
        """
        Get statistics about the link registry.
        
        Returns:
            dict: Statistics about the link registry
        """
        script_counts = {}
        
        for url, info in self.links["links"].items():
            script = info["script"]
            if script not in script_counts:
                script_counts[script] = 0
            script_counts[script] += 1
        
        return {
            "total_links": len(self.links["links"]),
            "by_script": script_counts,
            "created": self.links["metadata"]["created"],
            "last_updated": self.links["metadata"]["last_updated"]
        }
    
    def clear_registry(self):
        """Clear the link registry."""
        self.links = {
            "links": {},
            "metadata": {
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat()
            }
        }
        self._save_registry()

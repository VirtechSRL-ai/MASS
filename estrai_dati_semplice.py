import os
import json
import datetime
import time
import ssl
import urllib3
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import Optional, List

# Disabilita gli avvisi SSL per tutto lo script
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disabilita la verifica SSL per le richieste Python
ssl._create_default_https_context = ssl._create_unverified_context

# Import the LinkRegistry to avoid duplicate links
from link_registry import LinkRegistry

# Define schemas for different types of data
class ReferenceModel(BaseModel):
    title: str
    content: str
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None

class VideoModel(BaseModel):
    title: str
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    views: Optional[float] = None
    upload_date: Optional[str] = None

class LinkModel(BaseModel):
    title: str
    link: str
    source: str
    page_number: Optional[int] = None

class ReferencesSchema(BaseModel):
    references: List[ReferenceModel]

class VideosSchema(BaseModel):
    videos: List[VideoModel]

# Function to extract references using FirecrawlApp
def extract_references(keyword, domain):
    # Initialize the link registry
    registry = LinkRegistry()
    stats = registry.get_stats()
    print(f"\n[References] Link Registry Stats: {stats['total_links']} total links tracked")
    
    # Use FirecrawlApp (SSL verification is disabled globally)
    app = FirecrawlApp(api_key='fc-1877868d870648ed88570eb3e1322f3a')
    
    # Ensure domain has proper format for URL pattern
    if not domain.startswith(('http://', 'https://')):
        domain = f"https://{domain}"
    
    # Add wildcard if not present
    if not domain.endswith('*'):
        domain = f"{domain}/*"
    
    response = app.extract(
        urls=[domain],
        prompt=f'Extract all references and content related to {keyword}. Ensure that the title, content, and thumbnail images (if available) are included for each reference.',
        schema=ReferencesSchema.model_json_schema()
    )
    
    # Count the number of extracted references
    ref_count = 0
    references = []
    
    # Extract references from the response
    if hasattr(response, 'data') and hasattr(response.data, 'references'):
        references = response.data.references
    elif hasattr(response, 'data') and isinstance(response.data, dict) and 'references' in response.data:
        references = response.data['references']
    elif isinstance(response, dict) and 'data' in response and isinstance(response['data'], dict) and 'references' in response['data']:
        references = response['data']['references']
    
    original_ref_count = len(references)
    
    # Filter out duplicate URLs
    unique_urls = set()
    filtered_references = []
    
    for ref in references:
        url = None
        if isinstance(ref, dict) and 'url' in ref:
            url = ref['url']
        elif hasattr(ref, 'url'):
            url = ref.url
        
        if url:
            unique_urls.add(url)
    
    # Filter to only include new URLs
    new_urls = registry.filter_new_links(list(unique_urls), script_name='estrai_dati_semplice.py')
    
    # Filter references to only include those with new URLs
    for ref in references:
        url = None
        if isinstance(ref, dict) and 'url' in ref:
            url = ref['url']
        elif hasattr(ref, 'url'):
            url = ref.url
        
        if url and url in new_urls:
            filtered_references.append(ref)
    
    # Register the new URLs
    registry.register_links(new_urls, 'estrai_dati_semplice.py')
    
    # Replace the original references with filtered ones
    references = filtered_references
    ref_count = len(references)
    
    print(f"\n[References] TOTAL REFERENCES EXTRACTED: {original_ref_count}")
    print(f"[References] UNIQUE REFERENCES (NOT IN REGISTRY): {ref_count}")
    print(f"[References] FILTERED OUT: {original_ref_count - ref_count} duplicate references\n")
    
    # Update the response with filtered references if needed
    if isinstance(response, dict) and 'data' in response and isinstance(response['data'], dict) and 'references' in response['data']:
        response['data']['references'] = references
    
    # Save response to file in outputs directory
    save_response_to_file(response, keyword, "references", domain)
    
    return references

# Function to extract videos using FirecrawlApp
def extract_videos(keyword, domain):
    # Initialize the link registry
    registry = LinkRegistry()
    stats = registry.get_stats()
    print(f"\n[Videos] Link Registry Stats: {stats['total_links']} total links tracked")
    
    # Use FirecrawlApp (SSL verification is disabled globally)
    app = FirecrawlApp(api_key='fc-1877868d870648ed88570eb3e1322f3a')
    
    # Ensure domain has proper format for URL pattern
    if not domain.startswith(('http://', 'https://')):
        domain = f"https://{domain}"
    
    # Add wildcard if not present
    if not domain.endswith('*'):
        domain = f"{domain}/*"
    
    response = app.extract(
        urls=[domain],
        prompt=f'Extract all videos that include the keyword "{keyword}" in the page content. For each, include title, URL, thumbnail image URL, duration, views, and upload date.',
        schema=VideosSchema.model_json_schema()
    )
    
    # Count the number of extracted links
    video_count = 0
    videos = []
    
    if response and 'data' in response and 'videos' in response['data']:
        videos = response['data']['videos']
        original_count = len(videos)
        
        # Extract URLs from videos
        urls = []
        for video in videos:
            if 'url' in video:
                urls.append(video['url'])
        
        # Filter to only include new URLs
        new_urls = registry.filter_new_links(urls, script_name='estrai_dati_semplice.py')
        
        # Filter videos to only include those with new URLs
        filtered_videos = [
            video for video in videos
            if 'url' in video and video['url'] in new_urls
        ]
        
        # Register the new URLs
        registry.register_links(new_urls, 'estrai_dati_semplice.py')
        
        # Update the response with filtered videos
        response['data']['videos'] = filtered_videos
        videos = filtered_videos
        video_count = len(videos)
        
        print(f"\n[Videos] TOTAL LINKS EXTRACTED: {original_count}")
        print(f"[Videos] UNIQUE LINKS (NOT IN REGISTRY): {video_count}")
        print(f"[Videos] FILTERED OUT: {original_count - video_count} duplicate links\n")
    
    # Save response to file in outputs directory
    save_response_to_file(response, keyword, "videos", domain)
    
    return videos

# Function to extract links using FirecrawlApp
def extract_links(keyword, domain, num_pages=3):
    # Initialize the link registry
    registry = LinkRegistry()
    stats = registry.get_stats()
    print(f"\n[Links] Link Registry Stats: {stats['total_links']} total links tracked")
    
    # Ensure domain has proper format for URL pattern
    if not domain.startswith(('http://', 'https://')):
        domain = f"https://{domain}"
    
    # Create the app
    app = FirecrawlApp(api_key="fc-1877868d870648ed88570eb3e1322f3a")
    
    all_results = []
    already_seen_urls = set()  # Keep track of URLs we've already seen
    
    # Different strategies for different pages to ensure variety
    strategies = [
        # Page 1: Base strategy - main links from homepage
        {
            "url": domain,
            "prompt": f"Extract all links related to '{keyword}' from the homepage. Focus on primary navigation links and important sections."
        },
        # Page 2: Secondary links strategy
        {
            "url": f"{domain}/search?q={keyword.replace(' ', '+')}" if domain.endswith('/') else f"{domain}/search?q={keyword.replace(' ', '+')}",
            "prompt": f"Extract all links related to '{keyword}' from search results. Find links that weren't on the homepage."
        },
        # Page 3: Blog/content strategy
        {
            "url": f"{domain}/blog" if domain.endswith('/') else f"{domain}/blog",
            "prompt": f"Extract all blog posts or news articles related to '{keyword}'. Find recent content links."
        },
        # Fallback strategy for extra pages
        {
            "url": f"{domain}/about" if domain.endswith('/') else f"{domain}/about",
            "prompt": f"Extract all team, company, or about-related links that mention '{keyword}'."
        }
    ]
    
    # Ensure we have enough strategies for requested pages
    while len(strategies) < num_pages:
        strategies.append(strategies[-1])  # Duplicate last strategy as fallback
    
    # Process each page with its unique strategy
    for page in range(1, num_pages + 1):
        strategy_index = min(page - 1, len(strategies) - 1)
        strategy = strategies[strategy_index]
        
        print(f"Extracting data for page {page} using strategy {strategy_index + 1}...")
        
        try:
            # Extract data for the current page with specific strategy
            page_results = app.extract(
                [strategy["url"]],
                prompt=strategy["prompt"],
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the linked content"
                            },
                            "link": {
                                "type": "string",
                                "description": "The URL of the linked content"
                            },
                            "source": {
                                "type": "string",
                                "description": "The source or origin of the link"
                            }
                        },
                        "required": ["title", "link", "source"]
                    }
                }
            )
            
            # Gestisci il caso in cui page_results sia una tupla o un altro tipo non previsto
            if isinstance(page_results, tuple):
                print(f"Risultato inaspettato (tupla) dall'API: {page_results}")
                # Prova a estrarre i dati dalla tupla se possibile
                if len(page_results) > 0 and isinstance(page_results[0], dict):
                    page_results = list(page_results)
                else:
                    page_results = []
            
            # Filter out duplicates and add page number
            unique_results = []
            page_urls = []
            
            # Assicuriamoci che page_results sia una lista di dizionari
            if not isinstance(page_results, list):
                print(f"Convertendo page_results da {type(page_results)} a lista vuota")
                page_results = []
            
            for result in page_results:
                # Assicuriamoci che result sia un dizionario
                if not isinstance(result, dict):
                    print(f"Ignorando risultato non dizionario: {result}")
                    continue
                    
                # Estrai l'URL in modo sicuro
                url = result.get('link', '')
                if url and url not in already_seen_urls:
                    already_seen_urls.add(url)
                    page_urls.append(url)
                    result['page_number'] = page  # Explicitly set page number
                    unique_results.append(result)
            
            # Filter against the link registry
            new_urls = registry.filter_new_links(page_urls, script_name='estrai_dati_semplice.py')
            
            # Filter results to only include those with new URLs
            registry_filtered_results = [
                result for result in unique_results
                if result.get('link', '') in new_urls
            ]
            
            # Register the new URLs
            registry.register_links(new_urls, 'estrai_dati_semplice.py')
            
            # Add results from this page to the accumulated results
            all_results.extend(registry_filtered_results)
            print(f"Found {len(unique_results)} unique results for page {page}")
            print(f"After registry filtering: {len(registry_filtered_results)} new results")
            
        except Exception as e:
            print(f"Error extracting data for page {page}: {e}")
            # Try an alternative approach if the primary one fails
            try:
                # Fallback extraction with a more generic approach
                print(f"Trying fallback approach for page {page}...")
                fallback_url = f"{domain}?page={page}" if '?' not in domain else f"{domain}&page={page}"
                
                fallback_results = app.extract(
                    [fallback_url],
                    prompt=f"Extract any links related to '{keyword}' from page {page} that haven't been seen yet.",
                    schema={
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the linked content"
                                },
                                "link": {
                                    "type": "string",
                                    "description": "The URL of the linked content"
                                },
                                "source": {
                                    "type": "string",
                                    "description": "The source or origin of the link"
                                }
                            },
                            "required": ["title", "link", "source"]
                        }
                    }
                )
                
                # Gestisci il caso in cui fallback_results sia una tupla o un altro tipo non previsto
                if isinstance(fallback_results, tuple):
                    print(f"Risultato inaspettato (tupla) dall'API fallback: {fallback_results}")
                    # Prova a estrarre i dati dalla tupla se possibile
                    if len(fallback_results) > 0 and isinstance(fallback_results[0], dict):
                        fallback_results = list(fallback_results)
                    else:
                        fallback_results = []
                
                # Filter and add page number
                unique_fallback = []
                fallback_urls = []
                
                # Assicuriamoci che fallback_results sia una lista di dizionari
                if not isinstance(fallback_results, list):
                    print(f"Convertendo fallback_results da {type(fallback_results)} a lista vuota")
                    fallback_results = []
                
                for result in fallback_results:
                    # Assicuriamoci che result sia un dizionario
                    if not isinstance(result, dict):
                        print(f"Ignorando risultato fallback non dizionario: {result}")
                        continue
                        
                    # Estrai l'URL in modo sicuro
                    url = result.get('link', '')
                    if url and url not in already_seen_urls:
                        already_seen_urls.add(url)
                        fallback_urls.append(url)
                        result['page_number'] = page
                        unique_fallback.append(result)
                
                # Filter against the link registry
                new_fallback_urls = registry.filter_new_links(fallback_urls, script_name='estrai_dati_semplice.py')
                
                # Filter results to only include those with new URLs
                registry_filtered_fallback = [
                    result for result in unique_fallback
                    if result.get('link', '') in new_fallback_urls
                ]
                
                # Register the new URLs
                registry.register_links(new_fallback_urls, 'estrai_dati_semplice.py')
                
                all_results.extend(registry_filtered_fallback)
                print(f"Found {len(unique_fallback)} unique results with fallback approach")
                print(f"After registry filtering: {len(registry_filtered_fallback)} new results")
                
            except Exception as fallback_error:
                print(f"Fallback approach also failed: {fallback_error}")
        
        # Small delay between requests to avoid rate limiting
        if page < num_pages:
            time.sleep(1)
    
    # Save response to file in outputs directory
    formatted_results = {
        "total_results": len(all_results),
        "results": all_results,
        "metadata": {
            "pages_scraped": num_pages,
            "keyword": keyword,
            "domain": domain
        }
    }
    
    save_response_to_file(formatted_results, keyword, "links", domain)
    
    return all_results

# Helper function to save response to file
def save_response_to_file(response, query, content_type, website=None):
    # Create outputs directory if it doesn't exist
    outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    # Clean query for filename
    clean_query = ''.join(c if c.isalnum() else '_' for c in query)
    
    # Add domain to filename if provided
    domain = ""
    if website:
        domain = '_' + ''.join(c if c.isalnum() else '_' for c in website.replace('https://', '').replace('http://', '').split('/')[0])
    
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create filename
    filename = f"{content_type}_{clean_query}{domain}_{timestamp}.json"
    filepath = os.path.join(outputs_dir, filename)
    
    # Convert response to dictionary if it's not already one
    if not isinstance(response, dict):
        response_dict = response.__dict__ if hasattr(response, '__dict__') else {"error": "Could not convert response to JSON"}
    else:
        response_dict = response
    
    # Handle datetime objects in the response for JSON serialization
    def json_serial(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    # Write the response to the file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response_dict, f, indent=2, default=json_serial)
        print(f"\nOutput saved to: {filepath}")
    except Exception as e:
        print(f"Error saving output to file: {e}")

# Main function to extract data using all methods
def estrai_dati(keyword, dominio, num_pages=3):
    """
    Funzione unificata che estrae dati da un dominio usando diversi metodi di estrazione.
    
    Args:
        keyword (str): La parola chiave da cercare
        dominio (str): Il dominio su cui fare la ricerca
        num_pages (int, optional): Numero di pagine da analizzare per l'estrazione dei link. Default è 3.
        
    Returns:
        dict: Un dizionario contenente tutti i risultati combinati
    """
    print(f"\n=== INIZIO ESTRAZIONE DATI PER '{keyword}' SU '{dominio}' ===\n")
    
    # Esegui tutte le estrazioni in sequenza
    print("Estrazione riferimenti...")
    references = extract_references(keyword, dominio)
    
    print("Estrazione video...")
    videos = extract_videos(keyword, dominio)
    
    print("Estrazione link...")
    links = extract_links(keyword, dominio, num_pages)
    
    # Combina tutti i risultati
    combined_results = {
        "keyword": keyword,
        "domain": dominio,
        "timestamp": datetime.datetime.now().isoformat(),
        "references": references,
        "videos": videos,
        "links": links,
        "stats": {
            "total_references": len(references),
            "total_videos": len(videos),
            "total_links": len(links),
            "total_results": len(references) + len(videos) + len(links)
        }
    }
    
    # Salva i risultati combinati
    outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_keyword = ''.join(c if c.isalnum() else '_' for c in keyword)
    clean_domain = ''.join(c if c.isalnum() else '_' for c in dominio)
    
    output_file = os.path.join(outputs_dir, f"risultati_combinati_{clean_keyword}_{clean_domain}_{timestamp}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_results, f, ensure_ascii=False, indent=2, default=lambda o: o.dict() if hasattr(o, 'dict') else str(o))
    
    print(f"\n=== ESTRAZIONE COMPLETATA ===")
    print(f"Riferimenti trovati: {len(references)}")
    print(f"Video trovati: {len(videos)}")
    print(f"Link trovati: {len(links)}")
    print(f"Totale risultati: {len(references) + len(videos) + len(links)}")
    print(f"Risultati salvati in: {output_file}")
    
    return combined_results

# Funzione per eseguire l'estrazione da riga di comando
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Estrai dati da un dominio usando diversi metodi di estrazione.')
    parser.add_argument('keyword', type=str, help='Parola chiave da cercare')
    parser.add_argument('dominio', type=str, help='Dominio su cui fare la ricerca')
    parser.add_argument('--pagine', type=int, default=3, help='Numero di pagine da analizzare per l\'estrazione dei link (default: 3)')
    
    args = parser.parse_args()
    
    estrai_dati(args.keyword, args.dominio, args.pagine)

if __name__ == '__main__':
    main()

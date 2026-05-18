"""
Handler for news retrieval and information gathering operations.

This module provides a comprehensive interface for fetching and processing news articles
from various sources using the News API. It includes robust error handling, rate limiting,
and pagination support for reliable news data retrieval.

Capabilities:
    - Fetch news articles from multiple sources using News API
    - Filter news by date range with customizable time windows
    - Sort articles by relevance, popularity, or publication date
    - Support multiple languages (e.g., en, es, fr, de)
    - Domain filtering and exclusion for source control
    - Automatic rate limit management with backoff
    - Smart pagination handling for large result sets
    - Article metadata extraction (title, author, date, etc.)
    - Bulk article retrieval with configurable batch sizes
    - JSON output for easy data processing
    
API Requirements:
    - Requires a valid News API key stored in '/API/NEWS_API_KEY.txt'
    - Respects News API rate limits and usage guidelines
    - Handles API responses and errors gracefully

Usage Examples:
    Basic news search:
        fetch_news(API_KEY, "bitcoin", "2024-01-01")
    
    Advanced filtering:
        fetch_news(
            API_KEY,
            query="technology",
            from_date="2024-01-01",
            to_date="2024-01-31",
            language="en",
            domains="techcrunch.com,wired.com",
            exclude_domains="tabloids.com"
        )

Patterns:
    - "get news about {query}" - Basic news search
    - "search articles from {date}" - Date-based filtering
    - "find news in {language}" - Language-specific search
    - "get articles from {domains}" - Source-specific search
    - "exclude news from {domains}" - Source exclusion
    
Parameters:
    api_key (str): News API authentication key
    query (str): Search query for articles
    from_date (str): Start date in YYYY-MM-DD format
    to_date (str, optional): End date in YYYY-MM-DD format
    sort_by (str, optional): Sorting method ('relevancy', 'popularity', 'publishedAt')
    page_size (int, optional): Number of results per page (max 100)
    language (str, optional): Article language (e.g., 'en', 'es')
    domains (str, optional): Comma-separated list of domains to include
    exclude_domains (str, optional): Comma-separated list of domains to exclude

Returns:
    list: List of dictionaries containing article data including:
        - title: Article headline
        - source: Publishing source information
        - author: Article author(s)
        - publishedAt: Publication date
        - url: Article URL
        - description: Article summary
        - content: Article content preview
"""

import requests
import json
from datetime import datetime
import logging
import time
from pathlib import Path
from Jarvis_Agent_SDK.http_utils import make_api_request, RateLimiter, HttpError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Agent-related components loaded lazily on demand (not at import time)
# to avoid triggering the full boardroom/intelligence init chain
analyze_handler_capabilities = None
AgentBuilder = None

BASE_DIR = Path('~/Jarvis')  # Adjusted to correct base directory
api_key_file = BASE_DIR / 'API/NEWS_API_KEY.txt'

def load_api_key(file_path):
    """Load news API key from environment variable or file fallback."""
    env_key = os.environ.get('NEWS_API_KEY')
    if env_key:
        return env_key
    try:
        with file_path.open('r') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Unexpected error while loading API key: {e}")
        exit()

# Load the API key
try:
    API_KEY = load_api_key(api_key_file)
    print(f"Loaded API key: {API_KEY[:4]}...")
except FileNotFoundError:
    print(f"Error: API key file not found at {api_key_file}. Please ensure the file exists and contains your News API key.")
    exit()

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

async def fetch_news(api_key, query, from_date, to_date=None, sort_by='popularity', page_size=100, language=None, domains=None, exclude_domains=None):
    base_url = 'https://newsapi.org/v2/everything'
    # News API returns empty articles array with default python-httpx User-Agent
    _NEWS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"}
    params = {
        'q': query,
        'from': from_date,
        'sortBy': sort_by,
        'pageSize': page_size,
        'apiKey': api_key
    }
    if to_date:
        params['to'] = to_date
    if language:
        params['language'] = language
    if domains:
        params['domains'] = domains
    if exclude_domains:
        params['excludeDomains'] = exclude_domains
    articles = []
    page = 1
    while True:
        params['page'] = page
        logging.info(f"Fetching page {page}...")
        try:
            data = await make_api_request(
                url=base_url,
                method="GET",
                headers=_NEWS_HEADERS,
                params=params,
                timeout_seconds=30.0
            )
            
            if not data or data.get('status') != 'ok':
                logging.error(f"API Error: {data.get('message', 'Unknown error') if data else 'No response'}")
                break
                
            articles.extend(data.get('articles', []))
            total_results = data.get('totalResults', 0)
            logging.info(f"Fetched {len(data.get('articles', []))} articles. Total so far: {len(articles)} / {total_results}")
            if len(articles) >= total_results:
                logging.info("All articles fetched.")
                break
            page += 1
            
            # Small delay between requests
            import asyncio
            await asyncio.sleep(1)
            
        except HttpError as e:
            logging.error(f"HTTP Error: {e}")
            break
        except Exception as e:
            logging.error(f"Error fetching news: {e}")
            break
    return articles

if __name__ == '__main__':
    query = 'Apple'
    from_date = '2024-11-30'
    to_date = '2024-12-01'  # Optional
    language = 'en'  # Optional
    domains = 'apple.com,techcrunch.com'  # Optional
    exclude_domains = 'example.com'  # Optional
    
    if not is_valid_date(from_date):
        print("Invalid date format for 'from_date'. Please use 'YYYY-MM-DD'.")
        exit()
    if to_date and not is_valid_date(to_date):
        print("Invalid date format for 'to_date'. Please use 'YYYY-MM-DD'.")
        exit()
    
    import asyncio
    all_articles = asyncio.run(fetch_news(API_KEY, query, from_date, to_date=to_date, language=language, domains=domains, exclude_domains=exclude_domains))
    
    for article in all_articles:
        print(f"Title: {article['title']}")
        print(f"Source: {article['source']['name']}")
        print(f"Author: {article.get('author', 'Unknown')}")
        print(f"Published at: {article['publishedAt']}")
        print(f"URL: {article['url']}")
        print("\n")

    output_file = 'articles.json'
    with open(output_file, 'w') as f:
        json.dump(all_articles, f, indent=4)
    print(f"Articles saved to {output_file}")

# ─── MCP-compatible wrappers ───────────────────────────────────────

class NewsMCPHandler:
    """MCP-compatible class handler for news queries.
    
    Provides sync methods that the workspace MCP layer can call.
    Methods: fetch_news, search, handle
    """
    
    def __init__(self):
        self.name = "news"
        self.api_key = API_KEY
    
    def fetch_news(self, query: str, from_date: str = None, page_size: int = 5, context: dict = None, **kwargs) -> list:
        """Fetch news articles — primary MCP method."""
        return fetch_news_sync(query=query, from_date=from_date, page_size=min(int(page_size), 10))
    
    def search(self, query: str, **kwargs) -> list:
        """Alias for fetch_news."""
        return self.fetch_news(query, **kwargs)
    
    def handle(self, action: str = "fetch_news", **kwargs) -> dict:
        """Generic handler interface."""
        if action in ("fetch_news", "search"):
            articles = self.fetch_news(**kwargs)
            return {"status": "success", "articles": articles, "count": len(articles)}
        return {"status": "error", "error": f"Unknown action: {action}"}


def fetch_news_sync(query: str, from_date: str = None, page_size: int = 5, context: dict = None, **kwargs) -> list:
    """Synchronous news fetch — single request, no pagination.
    
    News API returns empty articles[] when User-Agent looks like a bot library.
    Uses httpx directly with a browser-like UA to avoid this.
    Returns list of article dicts (title, description, url, publishedAt, source).
    """
    import httpx
    from datetime import datetime, timedelta
    
    if from_date is None:
        from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    max_articles = min(page_size, 10)  # Hard cap for MCP usage
    try:
        resp = httpx.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": from_date,
                "sortBy": "popularity",
                "pageSize": max_articles,
                "language": "en",
                "apiKey": API_KEY,
            },
            headers={"User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"},
            timeout=30.0,
        )
        data = resp.json()
        if data.get("status") != "ok":
            logging.error("News API error: %s", data.get("message", "unknown"))
            return []
        return data.get("articles", [])[:max_articles]
    except Exception as e:
        logging.error(f"fetch_news_sync failed: {e}")
        return []

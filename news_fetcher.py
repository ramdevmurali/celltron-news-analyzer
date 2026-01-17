import os
import requests
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def _create_retry_session() -> requests.Session:
    """
    Creates a requests Session with automatic retry logic for resilience.
    
    Configuration:
    - Retries: 3 times
    - Backoff: 1s, 2s, 4s (exponential)
    - Triggers: 5xx server errors (not 4xx client errors)
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    # Mount handler for both HTTP and HTTPS
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

def _normalize_article(article: Dict) -> Optional[Dict]:
    """
    Normalizes a raw NewsAPI article and filters low-quality data.
    """
    title = article.get("title")
    
    # Filter: Garbage or Removed content
    if not title or title.strip() == "[Removed]":
        return None

    # Text Strategy: Prefer content, fallback to description
    raw_content = article.get("content")
    raw_description = article.get("description")
    
    # We strip to handle cases like " " which are technically not None
    text_payload = raw_content if (raw_content and raw_content.strip()) else raw_description

    # Validation: If we still have no text, the article is useless for analysis
    if not text_payload or not text_payload.strip():
        return None

    # Extraction: Safely get source name
    source_obj = article.get("source", {})
    source_name = source_obj.get("name", "Unknown")

    return {
        "title": title.strip(),
        "source": source_name,
        "published_at": article.get("published_at"),
        "url": article.get("url"),
        "text": text_payload.strip()
    }

def fetch_articles(topic: str, limit: int = 10) -> List[Dict]:
    """
    Fetches and validates news articles from NewsAPI.
    """
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_API_KEY not found in environment variables.")

    session = _create_retry_session()
    url = "https://newsapi.org/v2/everything"
    
    # Strategy: Fetch 2x the limit to account for filtered/removed articles
    page_size = min(100, limit * 2) 
    
    params = {
        "q": topic,
        "apiKey": api_key,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size
    }

    try:
        # TIMEOUT=10 is critical to prevent hanging processes
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status() 
        
        data = response.json()
        raw_articles = data.get("articles", [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

    valid_articles = []
    for art in raw_articles:
        normalized = _normalize_article(art)
        if normalized:
            valid_articles.append(normalized)
            
            # Stop exactly when we hit the requested limit
            if len(valid_articles) >= limit:
                break
                
    return valid_articles
import pytest
from news_fetcher import _normalize_article

def test_normalize_removed_article():
    """
    Test Case 1: Garbage Filtering
    Goal: Assert that articles with title '[Removed]' are immediately discarded.
    """
    raw_article = {
        "source": {"id": "google-news", "name": "Google News"},
        "author": None,
        "title": "[Removed]",
        "description": "[Removed]",
        "url": "https://google.com/removed",
        "urlToImage": None,
        "publishedAt": "2024-01-01T00:00:00Z",
        "content": "[Removed]"
    }
    
    result = _normalize_article(raw_article)
    assert result is None

def test_normalize_fallback_to_description():
    """
    Test Case 2: Content Strategy
    Goal: Assert that if 'content' is None/Empty, we successfully fallback to 'description'.
    """
    expected_text = "This is the description text."
    raw_article = {
        "source": {"id": "cnn", "name": "CNN"},
        "title": "Valid Title",
        "description": expected_text,
        "url": "https://cnn.com/article",
        "publishedAt": "2024-01-01T10:00:00Z",
        "content": None  # Simulating missing content
    }
    
    result = _normalize_article(raw_article)
    
    assert result is not None
    assert result["text"] == expected_text
    assert result["title"] == "Valid Title"

def test_normalize_valid_article():
    """
    Test Case 3: Happy Path
    Goal: Assert a standard article returns a dictionary with all required keys.
    """
    raw_article = {
        "source": {"id": "bbc", "name": "BBC News"},
        "title": "Election Updates",
        "description": "Short desc",
        "url": "https://bbc.com/news",
        "publishedAt": "2024-01-01T12:00:00Z",
        "content": "Full content of the article goes here."
    }
    
    result = _normalize_article(raw_article)
    
    assert result is not None
    # Check strict schema compliance
    assert result["source"] == "BBC News"
    assert result["text"] == "Full content of the article goes here."
    assert result["url"] == "https://bbc.com/news"
    assert "published_at" in result
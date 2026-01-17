import pytest
from unittest.mock import MagicMock, patch
from llm_analyzer import analyze_article, NewsAnalysis
import llm_analyzer

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_env():
    """
    Automatically mocks environment variables for all tests.
    Prevents actual API key checks from failing the tests.
    """
    with patch("llm_analyzer.os.getenv", return_value="fake_test_key"):
        yield

@pytest.fixture(autouse=True)
def reset_singleton():
    """
    Crucial: Resets the global _MODEL singleton in llm_analyzer before each test.
    Ensures that mocks do not leak between test cases.
    """
    llm_analyzer._MODEL = None
    yield
    llm_analyzer._MODEL = None

# --- Test Cases ---

@patch("llm_analyzer.genai.GenerativeModel")
@patch("llm_analyzer.genai.configure") # Mock configure to prevent network warning
def test_analyze_article_valid_json(mock_configure, mock_model_class):
    """
    Test Case 1: Valid API Response
    Goal: Verify that valid JSON from Gemini is correctly parsed into a NewsAnalysis object.
    """
    # 1. Setup Mock Response
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    # Simulate a perfect JSON response from Gemini
    valid_json = """
    {
        "gist": "The government passed a new finance bill.",
        "sentiment": "Positive",
        "tone": "Analytical",
        "confidence_score": 0.95
    }
    """
    mock_response.text = valid_json
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    # 2. Execute
    text = "This is a sufficiently long text regarding the new finance bill in India."
    result = analyze_article(text)

    # 3. Assertions
    assert result is not None
    assert isinstance(result, NewsAnalysis)
    assert result.sentiment == "Positive"
    assert result.confidence_score == 0.95
    assert result.gist == "The government passed a new finance bill."
    
    # Verify the prompt contained the input text
    args, _ = mock_instance.generate_content.call_args
    assert text in args[0]


def test_analyze_article_short_text():
    """
    Test Case 2: Input Validation (Guard Clause)
    Goal: Verify that short text returns None immediately and DOES NOT trigger the API.
    """
    # 1. Setup
    short_text = "Too short"
    
    # We patch the model class to ensure it is NEVER instantiated
    with patch("llm_analyzer.genai.GenerativeModel") as mock_model_class:
        # 2. Execute
        result = analyze_article(short_text)
        
        # 3. Assertions
        assert result is None
        
        # Critical: Prove that we saved an API call
        mock_model_class.assert_not_called()


@patch("llm_analyzer.genai.GenerativeModel")
@patch("llm_analyzer.genai.configure")
def test_analyze_article_api_failure(mock_configure, mock_model_class):
    """
    Test Case 3: API Failure Handling
    Goal: Verify that exceptions (e.g., 500 error) are caught and return None safely.
    """
    # 1. Setup Mock to raise an exception
    mock_instance = MagicMock()
    mock_instance.generate_content.side_effect = Exception("Google API Connection Reset")
    mock_model_class.return_value = mock_instance

    # 2. Execute
    text = "This is a valid long text but the API server is down."
    result = analyze_article(text)

    # 3. Assertions
    assert result is None
    # Verify we actually tried to call it
    mock_instance.generate_content.assert_called_once()
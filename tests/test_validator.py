import pytest
import requests
from unittest.mock import patch, MagicMock
from llm_validator import validate_analysis, ValidationResult

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_env():
    """
    Simulate the presence of the API key so the function attempts to run.
    """
    with patch("llm_validator.os.getenv", return_value="fake_openrouter_key"):
        yield

# --- Test Cases ---

@patch("llm_validator.requests.post")
def test_validate_analysis_timeout(mock_post):
    """
    Test Case 1: API Resilience
    Goal: Assert that if OpenRouter times out, the system catches the exception
    and returns None (skipping validation) rather than crashing the pipeline.
    """
    # 1. Setup Mock to raise Timeout
    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

    # 2. Execute
    text = "Some article text."
    analysis = {"gist": "summary", "sentiment": "Positive", "tone": "Neutral", "confidence_score": 0.9}
    
    result = validate_analysis(text, analysis)

    # 3. Assertions
    assert result is None
    # Verify we actually tried to call the URL
    mock_post.assert_called_once()


@patch("llm_validator.requests.post")
def test_validate_analysis_success(mock_post):
    """
    Test Case 2: Happy Path
    Goal: Assert that a valid JSON response from Mistral is correctly parsed
    into a ValidationResult object.
    """
    # 1. Setup Mock Response structure (OpenRouter format)
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    # Simulate the exact JSON structure returned by OpenRouter/Mistral
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"is_valid": true, "reasoning": "The sentiment matches the text perfectly."}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    # 2. Execute
    text = "India launches new solar initiative."
    analysis = {"gist": "Solar policy launched", "sentiment": "Positive", "tone": "Urgent", "confidence_score": 0.9}
    
    result = validate_analysis(text, analysis)

    # 3. Assertions
    assert result is not None
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.reasoning == "The sentiment matches the text perfectly."
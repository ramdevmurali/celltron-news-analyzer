import os
import json
import requests
from pydantic import ValidationError, BaseModel, Field

# --- Configuration ---
DEFAULT_MODEL_NAME = "mistralai/mistral-7b-instruct"

class ValidationResult(BaseModel):
    """
    Structured output for the validation step.
    Determines if the primary analysis accurately reflects the article text.
    """
    is_valid: bool = Field(
        description="True if the analysis (sentiment/gist) is supported by the text; False if hallucinations or errors are found."
    )
    reasoning: str = Field(
        description="Concise explanation citing specific quotes or logic from the text to support the validation verdict."
    )

def validate_analysis(original_text: str, analysis: dict) -> ValidationResult | None:
    """
    Validates the analysis using a secondary LLM (Mistral via OpenRouter).
    
    Args:
        original_text: The raw article text.
        analysis: The dictionary output from Gemini (gist, sentiment, etc.).
        
    Returns:
        ValidationResult object or None if validation fails/times out.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Warning: OPENROUTER_API_KEY missing. Skipping validation.")
        return None

    # Defensive: Truncate text to fit context window and reduce latency
    # Mistral-7B is capable, but 1000 chars is enough to verify sentiment.
    truncated_text = original_text[:1000] + "..." if len(original_text) > 1000 else original_text

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000", # Required by OpenRouter
        "X-Title": "Celltron Takehome",          # Required by OpenRouter
        "Content-Type": "application/json"
    }

    # Soft-code: Allow env var override
    model_name = os.getenv("VALIDATOR_MODEL", DEFAULT_MODEL_NAME)

    prompt = f"""
    Task: Validate if the following analysis accurately reflects the article text.
    
    Article Text (Truncated):
    "{truncated_text}"
    
    Analysis to Check:
    {json.dumps(analysis, indent=2)}
    
    Output Instructions:
    1. Respond ONLY with valid JSON.
    2. Format: {{"is_valid": boolean, "reasoning": "string"}}
    3. Check for hallucinations or wrong sentiment labels.
    """

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1 # Low temp for strict logic
    }

    try:
        # Timeout=10s is strict but necessary for a secondary step
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        # Parse OpenRouter response structure
        result_json = response.json()
        content = result_json['choices'][0]['message']['content']
        
        # Cleaning: Remove markdown backticks or conversational filler
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
            
        # Validation: Enforce schema
        validation = ValidationResult.model_validate_json(clean_content.strip())
        return validation

    except requests.exceptions.Timeout:
        print("Validation Skipped: OpenRouter API timed out.")
        return None
    except (requests.exceptions.RequestException, json.JSONDecodeError, ValidationError, KeyError) as e:
        print(f"Validation Error: {str(e)}")
        # Debug: print(f"Raw content: {content}") 
        return None
import os
import json
from typing import Optional, Literal
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
DEFAULT_MODEL_NAME = "gemini-2.5-flash"


# --- Pydantic Model (Unchanged) ---
class NewsAnalysis(BaseModel):
    gist: str = Field(description="A concise 1-2 sentence summary.")
    sentiment: Literal["Positive", "Negative", "Neutral"] = Field(description="Overall sentiment.")
    tone: str = Field(description="Stylistic tone.")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence level (0.0-1.0).")

# --- Module Globals ---
_MODEL = None

def _get_model():
    """
    Lazy initialization of the Gemini model.
    Ensures configuration happens only once.
    """
    global _MODEL
    if _MODEL is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing from environment.")
        
        genai.configure(api_key=api_key)
        
        # Soft-code: Allow env var override, default to flash
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)
        _MODEL = genai.GenerativeModel(model_name)
        
    return _MODEL

def analyze_article(text: str) -> Optional[NewsAnalysis]:
    """
    Analyzes article text using Gemini Pro.
    
    Args:
        text: Valid article text.
        
    Returns:
        NewsAnalysis object or None on failure/skipped.
    """
    # 1. Input Validation (Edge Case: Garbage/Short Text)
    if not text or len(text) < 50:
        print(f"Skipping Analysis: Text too short ({len(text) if text else 0} chars).")
        return None

    try:
        # 2. Get Model (Lazy Load)
        model = _get_model()
        
        prompt = f"""
        You are a strictly logical news analyst.
        
        Output Requirements:
        1. Return ONLY a valid JSON object.
        2. Do not use Markdown formatting (no ```json blocks).
        3. Strict Schema:
           - "gist": (str) 1-2 sentence summary.
           - "sentiment": (str) Exactly "Positive", "Negative", or "Neutral".
           - "tone": (str) e.g., "Urgent", "Analytical", "Satirical".
           - "confidence_score": (float) 0.0 to 1.0.

        Article Text:
        {text}
        """

        # 3. Call API
        response = model.generate_content(prompt)
        
        # 4. Handle Safety Blocks
        try:
            raw_output = response.text
        except ValueError:
            print("Analysis Failed: Content blocked by Gemini Safety Filters.")
            return None

        # 5. Clean & Parse
        clean_json = raw_output.strip().replace("```json", "").replace("```", "")
        analysis = NewsAnalysis.model_validate_json(clean_json)
        return analysis

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Parsing Error: {e}")
        return None
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None
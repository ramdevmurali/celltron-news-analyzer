
***

# Celltron News Analysis Pipeline

This repository contains a robust news analysis pipeline built for the Celltron Intelligence AI Engineer assignment. It implements Option A: Dual-LLM validation using Google Gemini and Mistral-7B.

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory and add your API keys:
```env
NEWSAPI_API_KEY=your_newsapi_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

### 3. Run Pipeline
```bash
python main.py
```
*   **Input:** Fetches current "India Politics" news.
*   **Output:** Generates a human-readable report in `output/final_report.md` and raw data in `output/analysis_results.json`.

### 4. Run Tests
To verify the analysis logic via mocked API calls:
```bash
python -m pytest tests/
```

## 📝 Documentation
For a detailed breakdown of the engineering decisions, architectural trade-offs, and iterative development process, please refer to:
**[DEVELOPMENT_PROCESS.md](./DEVELOPMENT_PROCESS.md)**
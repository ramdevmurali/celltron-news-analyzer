
***

# Development Process Log
## 0. Meta-Strategy (The System Prompt)
Before starting the task, I configured the AI assistant with a strict engineering persona to prevent "lazy coding" and ensure adherence to best practices.

**System Prompt Used:**
> "Act as a Senior Python Backend Engineer. You are my pair-programming partner.
> **The Philosophy:**
> 1. No 'Vibe Coding': Never generate code immediately. Plan first.
> 2. Defensive Engineering: Assume APIs will fail. Handle edge cases.
> 3. Documentation is Key: Track every decision.
>
> If I ask for something vague, criticize the prompt and ask for clarification."

## 1. Problem Understanding
**Goal:** Build a robust fact-checking pipeline for Indian political news. The system must fetch articles, use a primary LLM (Gemini) to analyze sentiment/tone, and a secondary LLM (Mistral via OpenRouter) to validate that analysis.
**Core Constraints:**
- Strict error handling (APIs are unstable).
- No "vibe coding" (Plan first, code second).
- Zero-cost architecture (Free tier limits).

## 2. Breakdown & Architecture
I broke the monolithic problem into 4 distinct modules to separate concerns:
1.  **Fetcher (`news_fetcher.py`):** Handles HTTP, retries, and data normalization.
2.  **Analyzer (`llm_analyzer.py`):** Encapsulates Gemini logic and Pydantic validation.
3.  **Validator (`llm_validator.py`):** Independent module for OpenRouter interaction.
4.  **Orchestrator (`main.py`):** Manages data flow and reporting.
### System Design & Data Flow
The pipeline follows a linear, defensive architecture to ensure data integrity at each stage:

[ NewsAPI ] 
    │
    ▼
[ news_fetcher.py ] ──► (Filter: [Removed] / Empty) ──► (Retry Logic)
    │
    ▼
[ llm_analyzer.py ] ──► (Schema: Pydantic) ──► (Model: Gemini 2.5)
    │
    ▼
[ llm_validator.py ] ──► (Audit: Mistral 7B) ──► (Verdict: is_valid)
    │
    ▼
[ main.py ] ──────────► (JSON Storage) ──► (Markdown Report)

**Design Rationale:**
- **Decoupling:** Each module can be tested independently (as seen in `/tests`).
- **Data Integrity:** The Pydantic layer in the Analyzer ensures that even if the LLM "hallucinates" the JSON structure, the system fails gracefully rather than passing corrupt data to the reporter.
- **Verification:** The Dual-LLM approach (Validation Layer) ensures that the final output isn't just "AI generated," but "AI verified."

## 3. AI Prompts & Iterations

### Phase 1: The Fetcher (Defensive Engineering)
**Strategy:** Instead of asking for "a script to fetch news," I built it function-by-function to ensure resilience.

*   **Prompt 1 (Network Layer):** "Write a helper function `_create_retry_session()` that returns a `requests.Session` with a `HTTPAdapter`. Config: 3 retries, backoff factor 1, retry on status 500, 502, 503, 504."
*   **Prompt 2 (Normalization):** "Write `_normalize_article(article: dict)`. Return `None` if title is '[Removed]'. Fallback to `description` if `content` is empty. Return a clean dict with specific keys."
*   **Prompt 3 (Main Logic):** "Write `fetch_articles(topic, limit)`. Use the retry session. Add `timeout=10` to the `.get()` call. Loop through results and stop exactly when `limit` valid articles are found."

### Phase 2: The Analyzer (Gemini)
**Strategy:** Define the data structure *before* the logic to prevent hallucinations.

*   **Prompt 4 (Data Model):** "Write a Pydantic model `NewsAnalysis` with fields: `gist`, `sentiment` (Literal: Positive/Negative/Neutral), `tone`, and `confidence_score` (0.0-1.0)."
*   **Prompt 5 (Implementation):** "Write `analyze_article(text)`. Use `google-generativeai`. Prompt for strict JSON without markdown. Clean the response string before parsing with `NewsAnalysis.model_validate_json`. Catch `StopCandidateException`."

**The Refactor (Human-in-the-Loop):**
*   **My Critique:** The initial code lacked a guard clause for empty text (wasting API calls) and re-configured the API key on every function call (inefficient).
*   **Refinement Prompt:** "Refactor `analyze_article`. 1) Return `None` if text < 50 chars. 2) Implement lazy loading for `genai.configure` so it only runs once."
*   **Result:** A much more efficient and safer module.

### Phase 3: The Validator (OpenRouter)
**Strategy:** Use a lightweight model to "unit test" the heavy model.

*   **Prompt 6:** "Write `validate_analysis(text, analysis_dict)`. Use `requests.post` to hit OpenRouter (Mistral 7B). Truncate text to 1000 chars. Ask: 'Does this analysis match the text?' Return a boolean `is_valid` and a string `reasoning`."

### Phase 4: Orchestration & Tests
*   **Prompt 7 (Pipeline):** "Write `run_pipeline`. Iterate through articles, analyze, then validate. Print status updates using standard `print` (avoid external deps like tqdm)."
*   **Prompt 8 (Reporting):** "Write `save_results`. Save raw JSON and generate a Markdown report with a Summary section (counting sentiments) and a Detailed Analysis section."
*   **Prompt 9 (Analyzer Tests):** "Write `tests/test_analyzer.py` using `pytest` and `unittest.mock`. 1) Mock valid JSON response. 2) Test short text guard clause (ensure no API call). 3) Test API failure handling."
*   **Prompt 10 (Fetcher Tests):** "Let's add `tests/test_fetcher.py`. I want to verify the `_normalize_article` logic specifically. Provide a mock raw article with title `[Removed]` -> Assert `None`. Provide a mock where `content` is `None` but `description` is valid -> Assert fallback. Provide a valid article -> Assert expected keys."
*   **Prompt 11 (Validator Tests):** "Finally, let's write `tests/test_validator.py`. We need to verify that our 'Dual LLM' pipeline handles OpenRouter failures gracefully. Mock `requests.post` to raise a `timeout`. Assert that `validate_analysis` returns `None` instead of crashing. Mock valid JSON response from Mistral -> Assert `ValidationResult` with correct boolean."

### Phase 5: Refactoring & Quality Tuning 
*   **Compliance Fix:** During final review, I realized the PDF required a separate `raw_articles.json` file.
    *   *Action:* Refactored `save_results` to extract and save raw data before processing the analysis report.
*   **Data Quality Iteration:** The initial search query "India Politics" returned irrelevant noise (e.g., generic Bollywood news or international mentions).
    *   *Fix:* Updated the search query to `' "Indian Government" '` (nested quotes for exact phrase match) and increased the article limit to 12.
    *   *Result:* Signal-to-noise ratio improved significantly; retrieved articles were strictly political.

## 4. Decisions & Trade-offs
1.  **Pydantic vs. Raw Dicts:** I chose Pydantic because LLMs often output malformed JSON. Pydantic's `model_validate_json` provides a strict gatekeeper, ensuring the rest of the code never crashes due to missing keys.
2.  **Over-fetching Strategy:** In `news_fetcher`, I requested `limit * 2` articles from the API. This ensures that after filtering out `[Removed]` or empty articles, the user still gets the requested number of results without needing a second API call.
3.  **Lazy Loading:** Moving `genai.configure` to a lazy loader prevented global scope issues during testing and improved performance for batch processing.
4.  **Synchronous vs. Asynchronous Architecture:**
    *   **Decision:** I chose a synchronous execution model (`requests` + `time.sleep`) rather than `asyncio`/`aiohttp`.
    *   **Reasoning:**
        *   *Rate Limit Stability:* The free-tier APIs (Gemini/OpenRouter) have strict requests-per-minute limits. Async concurrency would require complex semaphore implementation to prevent `429 Too Many Requests` errors.
        *   *Simplicity:* For a small batch size (12 articles), the difference in runtime is negligible, but the code complexity is significantly lower, making it more maintainable.
        *   *Future Scaling:* For a high-throughput production system, I would refactor this to use Celery workers or an `asyncio` pipeline with token-bucket rate limiting.

## 5. Testing Strategy
I implemented a multi-layered `pytest` suite (8 tests total) to ensure system reliability:
1.  **Analyzer Tests:** Verified Gemini integration and the 50-char guard clause using mocks to ensure zero-cost execution.
2.  **Fetcher Tests:** Verified the data normalization logic, specifically ensuring that `[Removed]` titles are caught and the content-to-description fallback is reliable.
3.  **Validator Tests:** Verified the "Dual LLM" safety net by mocking OpenRouter timeouts and malformed JSON responses.
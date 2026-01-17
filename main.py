import time
from typing import List, Dict
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Internal Modules
import news_fetcher
import llm_analyzer
import llm_validator

def run_pipeline(topic: str, limit: int) -> List[Dict]:
    """
    Orchestrates the News Analysis Pipeline: Fetch -> Analyze -> Validate.
    
    Args:
        topic: The search topic for NewsAPI.
        limit: Max number of articles to process.
        
    Returns:
        List of dictionaries containing raw data, analysis, and validation results.
    """
    print(f"\n🚀 Starting Pipeline | Topic: '{topic}' | Limit: {limit}")
    
    # 1. Fetch Phase
    print("Step 1: Fetching articles from NewsAPI...")
    articles = news_fetcher.fetch_articles(topic, limit)
    total_found = len(articles)
    
    if total_found == 0:
        print("❌ No articles found. Aborting.")
        return []
        
    print(f"✅ Found {total_found} valid articles. Beginning analysis loop.\n")
    
    results = []
    
    # 2. Processing Phase
    for i, article in enumerate(articles, 1):
        title_snippet = article['title'][:50] + "..."
        print(f"[{i}/{total_found}] Processing: {title_snippet}")
        
        # A. Analyze (Gemini)
        print("   Running Gemini Analysis...", end=" ", flush=True)
        analysis_model = llm_analyzer.analyze_article(article['text'])
        
        if not analysis_model:
            print("FAILED (Skipping)")
            continue
        print("DONE")
        
        # Convert Pydantic model to dict for usage
        analysis_dict = analysis_model.model_dump()
        
        # B. Validate (Mistral)
        print("   Running Mistral Validation...", end=" ", flush=True)
        # Note: Mistral requires a dict, not the Pydantic object
        validation_model = llm_validator.validate_analysis(article['text'], analysis_dict)
        
        if validation_model:
            print(f"DONE (Valid: {validation_model.is_valid})")
            validation_dict = validation_model.model_dump()
        else:
            print("SKIPPED (Timeout/Error)")
            validation_dict = None

        # C. Aggregate
        entry = {
            "article": article,
            "analysis": analysis_dict,
            "validation": validation_dict
        }
        results.append(entry)
        
        # Rate Limit Courtesy: Brief pause between heavy LLM calls
        time.sleep(1) 

    print(f"\n🎉 Pipeline Complete. Processed {len(results)}/{total_found} articles successfully.")
    return results

def save_results(results: List[Dict]):
    """
    Saves:
    1. Raw articles to output/raw_articles.json (REQUIRED BY PDF)
    2. Full analysis to output/analysis_results.json
    3. Human-readable report to output/final_report.md
    """
    # Ensure output directory exists
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # --- CHANGE 1: Save Raw Articles Separately ---
    raw_articles = [item["article"] for item in results]
    raw_path = output_dir / "raw_articles.json"
    try:
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_articles, f, indent=2, ensure_ascii=False)
        print(f"💾 Raw articles saved to: {raw_path}")
    except IOError as e:
        print(f"❌ Error saving raw JSON: {e}")

    # --- End CHANGE 1 ---

    # 2. Save Analysis Results (Same as before)
    json_path = output_dir / "analysis_results.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Analysis results saved to: {json_path}")
    except IOError as e:
        print(f"❌ Error saving analysis JSON: {e}")

    # 3. Generate Markdown Report (Same as before)
    md_path = output_dir / "final_report.md"
    
    # Calculate Stats
    total = len(results)
    stats = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for item in results:
        sentiment = item["analysis"]["sentiment"]
        if sentiment in stats:
            stats[sentiment] += 1

    # Build Report Content
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "# News Analysis Report",
        f"**Date:** {current_time}",
        f"**Articles Analyzed:** {total}",
        "**Source:** NewsAPI",
        "",
        "## Summary",
        f"- Positive: {stats['Positive']} articles",
        f"- Negative: {stats['Negative']} articles",
        f"- Neutral: {stats['Neutral']} articles",
        "",
        "## Detailed Analysis"
    ]

    for i, item in enumerate(results, 1):
        art = item["article"]
        anl = item["analysis"]
        val = item["validation"]

        lines.append(f"### Article {i}: \"{art['title']}\"")
        lines.append(f"- **Source:** {art['source']} ([Link]({art['url']}))")
        lines.append(f"- **Gist:** {anl['gist']}")
        lines.append(f"- **Tone:** {anl['tone']}")
        lines.append(f"- **LLM#1 Sentiment:** {anl['sentiment']} (Conf: {anl['confidence_score']})")
        
        if val:
            icon = "✓" if val["is_valid"] else "⚠️"
            status = "Correct" if val["is_valid"] else "Flagged"
            lines.append(f"- **LLM#2 Validation:** {icon} {status}. {val['reasoning']}")
        else:
            lines.append("- **LLM#2 Validation:** ❓ Skipped (Timeout/Error)")
            
        lines.append("")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"📄 Report generated at: {md_path}")
    except IOError as e:
        print(f"❌ Error saving Markdown: {e}")
        # --- ADD THIS AT THE VERY BOTTOM ---

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the pipeline
    # Topic is specific to the assignment requirement
    final_data = run_pipeline("India Politics", limit=5)
    
    # Save output only if we have data
    if final_data:
        save_results(final_data)
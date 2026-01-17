import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env")
else:
    print(f"✅ Found API Key: {api_key[:5]}...")
    
    try:
        genai.configure(api_key=api_key)
        
        print("\n🔍 Querying Google API for available models...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
                available_models.append(m.name)
        
        if not available_models:
            print("\n⚠️ No models found. Check if your API Key has the 'Generative Language API' enabled in Google Cloud Console.")
            
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
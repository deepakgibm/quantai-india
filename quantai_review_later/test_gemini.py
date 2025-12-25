"""Quick test to check Gemini API directly"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key configured: {api_key[:20] if api_key else 'NOT FOUND'}...")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # List available models
        print("\nListing available models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
        
        # Try to use the model
        print("\nTrying gemini-1.5-flash...")
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say hello")
        print(f"Success! Response: {response.text}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTrying gemini-pro...")
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content("Say hello")
            print(f"Success! Response: {response.text}")
        except Exception as e2:
            print(f"Also failed: {str(e2)}")
else:
    print("No API key found!")

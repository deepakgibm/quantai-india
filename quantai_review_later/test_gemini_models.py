import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key: {api_key[:10]}...")

genai.configure(api_key=api_key)

models = ['gemini-pro', 'gemini-1.5-flash', 'gemini-2.0-flash']

for model_name in models:
    print(f"\nTesting model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, how are you?")
        print(f"Success! Response: {response.text[:50]}...")
    except Exception as e:
        print(f"Failed: {str(e)}")

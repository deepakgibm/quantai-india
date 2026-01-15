# Ensure API key is provided via environment variable or CLI arg
import os
import sys
import google.generativeai as genai

def get_working_model():
    """
    Dynamically finds the best available 'flash' model 
    to prevent 404 errors.
    """
    print("Checking available models...")
    try:
        for m in genai.list_models():
            # In 2026, we look for 2.0 or 2.5 flash models first
            # but fall back to whatever 'flash' model is active
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    print(f"✅ Found working model: {m.name}")
                    return m.name
    except Exception as e:
        print(f"❌ Could not list models: {e}")
    
    # Default fallback if listing fails (Standard for early 2026)
    return 'gemini-2.0-flash'


def validate_api_key(sample_model=None):
    """Validate the configured API key by listing models and making
    a minimal generation call against a selected model.
    Returns (True, model_id) if valid, else (False, error_message).
    """
    try:
        models = list(genai.list_models())
        if not models:
            return False, "No models returned from list_models()"

        # Choose a sample model if not provided
        model_id = sample_model or next((m.name for m in models if 'flash' in m.name), models[0].name)

        # Try a tiny generation to ensure the key can call the model
        try:
            model = genai.GenerativeModel(model_id)
            resp = model.generate_content("Ping")
            # Consider success if we get any text back
            text = getattr(resp, 'text', None) or getattr(resp, 'candidates', None)
            if text:
                return True, model_id
            return False, "Model call returned no content"
        except Exception as e:
            return False, f"Model generation failed: {e}"

    except Exception as e:
        return False, f"Could not list models: {e}"

def run_gemini_test():
    # Automatically get the correct model name
    model_id = get_working_model()
    
    print(f"--- Initializing {model_id} ---")
    
    try:
        # Initialize the model
        model = genai.GenerativeModel(model_id)
        
        # Simple test prompt
        prompt = "Hello! Verify that you are working. What is your model version?"
        
        # Generate content
        response = model.generate_content(prompt)
        
        print("\n--- Response ---")
        print(response.text)
        print("----------------")
        print("✅ SUCCESS: API is connected and model is responding.")

    except Exception as e:
        print("\n❌ STILL ERRORING:")
        print(str(e))
        print("\nTROUBLESHOOTING TIPS:")
        print("1. Ensure your API Key is valid and has billing enabled (if required).")
        print("2. Check if your region is supported for the 2.x series models.")
        print("3. Try 'gemini-1.5-flash-latest' specifically if 'gemini-1.5-flash' failed.")

if __name__ == "__main__":
    # Configure API key from env or first CLI arg
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GENAI_API_KEY")
    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]

    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            print(f"Failed to configure genai: {e}")
            sys.exit(1)
    else:
        print("No API_KEY or ADC found. Please either:\n"
              "  - Set the `GOOGLE_API_KEY` environment variable.\n"
              "  - Pass the key as the first CLI argument.\n"
              "  - Or set up Application Default Credentials (ADC).")
        sys.exit(1)

    # Validate API key by listing models and making a tiny generation call
    valid, info = validate_api_key()
    if not valid:
        print("API key validation failed:", info)
        sys.exit(1)

    print(f"API key validated. Using model: {info}")
    run_gemini_test()
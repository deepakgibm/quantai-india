import logging
import google.generativeai as genai
from typing import Any
from config import settings
from fastapi import HTTPException
import json
import re

logger = logging.getLogger(__name__)

class AIProvider:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIProvider, cls).__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model_name = self._get_working_model()
                self._model = genai.GenerativeModel(model_name)
                logger.info(f"AIProvider: Initialized Gemini model: {model_name}")
            except Exception as e:
                logger.error(f"AIProvider: Failed to initialize Gemini AI: {e}")
                self._model = None
        else:
            logger.warning("AIProvider: GEMINI_API_KEY not set")
            self._model = None

    def _get_working_model(self) -> str:
        """Dynamically finds the best available 'flash' model."""
        try:
            models = list(genai.list_models())
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            
            # 1. Prioritize flash models (2.0 > 1.5 > pro)
            flash_20 = [m for m in available_models if 'gemini-2.0-flash' in m.lower()]
            if flash_20: return sorted(flash_20, reverse=True)[0]
            
            flash_15 = [m for m in available_models if 'gemini-1.5-flash' in m.lower()]
            if flash_15: return sorted(flash_15, reverse=True)[0]
            
            # 2. Fallback to standard models
            if "models/gemini-pro" in available_models: return "models/gemini-pro"
            if "models/gemini-1.5-pro" in available_models: return "models/gemini-1.5-pro"
            
            return "gemini-1.5-flash"
        except Exception as e:
            logger.warning(f"AIProvider: Model listing failed: {e}. Falling back to default.")
            return "gemini-1.5-flash"

    async def generate_content(self, prompt: str) -> str:
        """Generate content from the AI model."""
        from core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
        
        # Initialize CB on first use if not exists (or in __init__)
        if not hasattr(self, '_cb'):
            self._cb = CircuitBreaker("GeminiAI", failure_threshold=3, recovery_timeout=60.0)
            
        if not self._model:
            raise HTTPException(status_code=503, detail="Gemini AI service unavailable")
        
        async def _call_gemini():
            return await self._model.generate_content_async(prompt)
            
        try:
            logger.info(f"AIProvider: Processing prompt with model {self._model.model_name}")
            response = await self._cb.call(_call_gemini)
            
            if not response or not response.candidates:
                logger.error("AIProvider: Empty response or no candidates")
                raise ValueError("Empty response from AI")
                
            return response.text.strip()
            
        except CircuitBreakerOpenException:
            logger.error("AIProvider: Circuit Open - Gemini API Unavailable")
            raise HTTPException(status_code=503, detail="AI Service temporarily unavailable (Circuit Open)")
            
        except HTTPException:
            raise
            
        except Exception as e:
             # Check if it's a safety block
            error_msg = str(e)
            if "safety" in error_msg.lower():
                error_msg = "Response blocked by safety filters."
            
            logger.error(f"AIProvider: Generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"AI processing error: {error_msg}")

    def extract_json(self, text: str) -> Any:
        # ... (rest of method)
        """Extract JSON from potential markdown text."""
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            # Try parsing
            return json.loads(text)
        except json.JSONDecodeError:
            # Try regex extraction
            json_match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL) or re.search(r'{\s*".*"\s*:.*}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("Failed to parse JSON from AI response")

_provider = None
def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = AIProvider()
    return _provider

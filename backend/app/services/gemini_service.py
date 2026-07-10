import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None

    @property
    def client(self):
        if not self._client and self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Error initializing Gemini client: {e}")
        return self._client

    def _sync_generate(self, prompt: str, system_instruction: Optional[str] = None, response_mime_type: Optional[str] = None) -> str:
        if not self.client:
            raise ValueError("Gemini API key is not configured or client failed to initialize.")
        
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        if response_mime_type:
            config["response_mime_type"] = response_mime_type

        # Use new client structure
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(**config) if config else None
        )
        return response.text

    async def analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Detects language, intent, emergency status, and query category of the user's message.
        """
        fallback = {
            "detected_language": "en",
            "intent": "general",
            "is_emergency": False,
            "query_category": "general",
            "entities": {}
        }
        
        if not self.api_key:
            logger.warning("Gemini API key not found. Using fallback analysis.")
            return fallback

        prompt = f"""Analyze the following message from a fan at the FIFA World Cup 2026 stadium:
"{message}"

Return ONLY a JSON object with this exact structure:
{{
  "detected_language": "ISO 639-1 code (e.g., en, hi, es, fr, ar, pt)",
  "intent": "one of: navigation, food, facilities, emergency, match_info, general",
  "is_emergency": true/false (true only if it indicates an immediate threat like injury, medical issue, security threat, fire, or lost child),
  "query_category": "suitable short category name (e.g. food_search, toilet_find, gate_nav, emergency_help, general_greet)",
  "entities": {{
     "location_type": "concessions/washroom/first_aid/gate/exit/section/stairs if specified, else null",
     "location_name": "name of food, stall, or location if mentioned, else null"
  }}
}}"""

        try:
            # We can use response_mime_type="application/json" for structured output
            loop = asyncio.get_running_loop()
            result_text = await loop.run_in_executor(
                None,
                self._sync_generate,
                prompt,
                "You are an expert natural language analyzer for a smart stadium assistant.",
                "application/json"
            )
            data = json.loads(result_text.strip())
            return data
        except Exception as e:
            logger.error(f"Error during message analysis: {e}")
            # Try to manually parse if JSON failed, or return fallback
            return fallback

    async def generate_response(self, message: str, language: str, intent: str, context: Dict[str, Any]) -> str:
        """
        Generates a natural-language response in the detected language using stadium context.
        """
        if not self.api_key:
            return f"[Demo Mode] Thank you for your question: '{message}'. To enable full AI answers, please configure the GEMINI_API_KEY. Current context: {context}"

        context_str = json.dumps(context, indent=2, ensure_ascii=False)
        
        prompt = f"""You are 'Stadium Saathi', the smart GenAI assistant for World Cup Arena 2026.
You are helping a fan in the stadium.

Fan Message: "{message}"
Detected Language (ISO code): "{language}"
Intent: "{intent}"
Stadium Context (JSON):
{context_str}

CRITICAL RULES:
1. You MUST respond in the language code: "{language}". For example, if it is 'hi', respond in Hindi; if 'es', in Spanish; if 'ar', in Arabic; if 'fr', in French; if 'pt', in Portuguese; if 'en', in English.
2. Be friendly, encouraging, and clear.
3. Keep the response concise (2-4 sentences is best unless explaining directions).
4. If the intent is navigation, explain the route step-by-step using the path details provided in the context. Mention if any zone was avoided due to high crowd density.
5. If the fan asks for food or washrooms, guide them using the facilities data in the context.
6. If an emergency was detected (medical/security/lost child), assure them that staff has been notified, and guide them to the nearest first-aid or help point immediately.
7. NEVER make up features or locations not present in the context.
"""

        try:
            loop = asyncio.get_running_loop()
            response_text = await loop.run_in_executor(
                None,
                self._sync_generate,
                prompt,
                "You are Stadium Saathi, a multi-lingual helper assistant."
            )
            return response_text.strip()
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return f"Thank you. We are looking into your query. (Fallback: {message})"

    async def generate_directions(self, path: List[Dict[str, Any]], language: str, avoided_zones: List[str] = None) -> str:
        """
        Converts a raw BFS path list into natural-language walking instructions.
        """
        if not self.api_key:
            path_names = " -> ".join([p["name"] for p in path])
            return f"Route: {path_names}"

        path_json = json.dumps(path, indent=2)
        avoided_str = ", ".join(avoided_zones) if avoided_zones else "None"
        
        prompt = f"""Convert the following path of locations in a stadium into clear, step-by-step walking directions for a fan.
Path (JSON list of locations in order from start to destination):
{path_json}

Avoided Zones (due to high crowd): {avoided_str}

CRITICAL RULES:
1. Write the directions in the language matching ISO code: "{language}".
2. Be highly descriptive about the transitions. E.g., if level changes (from L0 to L1) via stairs, make it very clear they need to take the stairs.
3. Keep it brief but easy to follow.
4. Mention if we took an alternate route to avoid crowded zones.
"""
        try:
            loop = asyncio.get_running_loop()
            directions_text = await loop.run_in_executor(
                None,
                self._sync_generate,
                prompt,
                "You are an indoor stadium navigation assistant."
            )
            return directions_text.strip()
        except Exception as e:
            logger.error(f"Error generating directions: {e}")
            path_names = " -> ".join([p["name"] for p in path])
            return f"Path: {path_names}"

gemini_service = GeminiService()

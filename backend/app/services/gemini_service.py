import os
import json
import asyncio
import hashlib
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.core.config import settings

# ✅ IMPROVEMENT: Use proper logging instead of print()
logger = logging.getLogger(__name__)

# Define Pydantic schemas for Gemini structured outputs
class IntentExtraction(BaseModel):
    detected_language: str = Field(description="ISO 639-1 language code or full language name of the fan's message")
    intent: str = Field(description="Intent category: 'navigation', 'facility_query', 'general_info', 'emergency', 'greeting', or 'other'")
    is_emergency: bool = Field(description="True if this is an emergency like medical distress, security issue, fire, or danger")
    start_location: Optional[str] = Field(None, description="Extracted starting location name or ID if mentioned in the query")
    end_location: Optional[str] = Field(None, description="Extracted destination location name, type, or ID if mentioned in the query")
    facility_type: Optional[str] = Field(None, description="If looking for a facility type, extract one of: 'gate', 'section', 'food_stall', 'washroom', 'first_aid', 'escalator', 'exit'")

class FinalResponse(BaseModel):
    response: str = Field(description="A friendly, helpful response in the SAME language the fan used.")
    is_emergency: bool = Field(description="True if an emergency is detected")


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None

        # ✅ IMPROVEMENT: In-memory caches to avoid redundant Gemini calls
        self._intent_cache: Dict[str, IntentExtraction] = {}
        self._response_cache: Dict[str, str] = {}

        # Check if API key is valid and not placeholder
        if self.api_key and "your_gemini_api_key" not in self.api_key.lower():
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini Client initialized successfully.")
            except Exception as e:
                logger.error("Failed to initialize Gemini Client: %s", e)
        else:
            logger.warning("Gemini API Key is missing or placeholder. Running in Mock Mode.")

    def is_mock_mode(self) -> bool:
        return self.client is None

    def _make_cache_key(self, *args: str) -> str:
        """Create a stable MD5 hash key from multiple string arguments."""
        combined = "|".join(a.strip().lower() for a in args if a)
        return hashlib.md5(combined.encode()).hexdigest()

    async def extract_intent(self, message: str) -> IntentExtraction:
        """Step 1: Extract intent, language, and location entities from user message."""
        if self.is_mock_mode():
            return self._mock_extract_intent(message)

        # ✅ IMPROVEMENT: Return cached result for identical messages
        cache_key = self._make_cache_key(message)
        if cache_key in self._intent_cache:
            logger.debug("Cache hit for extract_intent: %s", message[:40])
            return self._intent_cache[cache_key]

        prompt = f"""
        Analyze this user message from a stadium visitor at a FIFA World Cup 2026 match.
        Extract the language, core intent, start/end locations, and any facility type being searched for.
        
        Message: "{message}"
        """

        try:
            # ✅ IMPROVEMENT: run_in_executor prevents blocking the async event loop
            # The google-genai SDK's generate_content() is synchronous — wrapping it
            # means FastAPI can handle other requests while Gemini processes this one.
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=IntentExtraction,
                        system_instruction=(
                            "You are an expert multilingual classifier for stadium inquiries. "
                            "Accurately categorize the user intent and extract locations. "
                            "Be conservative with emergencies: only set is_emergency=true if "
                            "there is a medical issue, security threat, fire, or immediate danger."
                        )
                    )
                )
            )

            data = json.loads(response.text)
            result = IntentExtraction(**data)

            # ✅ Cache result (don't cache emergencies — always re-evaluate)
            if not result.is_emergency:
                self._intent_cache[cache_key] = result

            return result

        # ✅ IMPROVEMENT: Specific exception types instead of bare except
        except json.JSONDecodeError as e:
            logger.warning("Gemini returned invalid JSON in extract_intent: %s. Using mock.", e)
            return self._mock_extract_intent(message)
        except Exception as e:
            logger.error("Gemini extract_intent error: %s. Falling back to mock.", e)
            return self._mock_extract_intent(message)

    async def generate_response(
        self,
        message: str,
        detected_language: str,
        intent: str,
        navigation_context: Optional[str] = None,
        crowd_alert: Optional[str] = None
    ) -> str:
        """Step 2: Generate the final friendly response in the user's language using context."""
        if self.is_mock_mode():
            return self._mock_generate_response(
                message, detected_language, intent, navigation_context, crowd_alert
            )

        # ✅ IMPROVEMENT: Cache final responses (skip cache if crowd data is involved,
        # since crowd density changes every few seconds)
        if not crowd_alert:
            cache_key = self._make_cache_key(message, detected_language, intent, navigation_context or "")
            if cache_key in self._response_cache:
                logger.debug("Cache hit for generate_response: %s", message[:40])
                return self._response_cache[cache_key]

        prompt = f"""
        User Message: "{message}"
        Language to use: {detected_language}
        Intent category: {intent}
        """
        if navigation_context:
            prompt += f"\nNavigation Route Info: {navigation_context}"
        if crowd_alert:
            prompt += f"\nCrowd Congestion Alert: {crowd_alert}"

        system_instr = """
        You are "Stadium Saathi", a friendly, helpful GenAI-powered multi-language assistant for FIFA World Cup 2026 stadium visitors.
        Your goals:
        1. ALWAYS respond in the SAME language the fan used (indicated in the prompt).
        2. Be warm, welcoming, and concise. Keep instructions simple.
        3. If navigation or route info is provided, present the step-by-step directions clearly.
        4. If a crowd alert is provided, warn the fan clearly and suggest the alternative route.
        5. For emergencies, provide calm, clear guidance and direct them to the nearest staff or first-aid.
        6. Never mention technical details like node IDs or graph algorithms.
        """

        try:
            # ✅ IMPROVEMENT: Non-blocking call via run_in_executor
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=FinalResponse,
                        system_instruction=system_instr
                    )
                )
            )

            data = json.loads(response.text)
            result_text: str = data.get("response", "")

            # ✅ Cache non-crowd responses
            if not crowd_alert and result_text:
                cache_key = self._make_cache_key(message, detected_language, intent, navigation_context or "")
                self._response_cache[cache_key] = result_text

            return result_text

        except json.JSONDecodeError as e:
            logger.warning("Gemini returned invalid JSON in generate_response: %s. Using mock.", e)
            return self._mock_generate_response(
                message, detected_language, intent, navigation_context, crowd_alert
            )
        except Exception as e:
            logger.error("Gemini generate_response error: %s. Falling back to mock.", e)
            return self._mock_generate_response(
                message, detected_language, intent, navigation_context, crowd_alert
            )

    # ------------------------------------------------------------------ #
    #  Mock mode helpers (unchanged from original)                         #
    # ------------------------------------------------------------------ #

    def _mock_extract_intent(self, message: str) -> IntentExtraction:
        """Rule-based fallback when Gemini API is unavailable."""
        message_lower = message.lower()
        intent = "general_info"
        is_emergency = False
        start_location = None
        end_location = None
        facility_type = None

        emergency_keywords = ["help", "emergency", "fire", "medical", "hurt", "injured", "lost child", "security"]
        navigation_keywords = ["how do i get", "where is", "find", "navigate", "directions to", "take me to", "go to"]
        facility_keywords = {
            "washroom": "washroom", "toilet": "washroom", "bathroom": "washroom", "restroom": "washroom",
            "food": "food_stall", "eat": "food_stall", "drink": "food_stall",
            "gate": "gate", "entrance": "gate", "exit": "exit",
            "first aid": "first_aid", "medical": "first_aid",
            "escalator": "escalator", "elevator": "escalator",
        }

        if any(kw in message_lower for kw in emergency_keywords):
            if any(kw in message_lower for kw in ["fire", "medical", "hurt", "injured", "lost child"]):
                is_emergency = True
                intent = "emergency"

        if any(kw in message_lower for kw in navigation_keywords):
            intent = "navigation"

        for keyword, ftype in facility_keywords.items():
            if keyword in message_lower:
                intent = "facility_query"
                facility_type = ftype
                break

        # Detect language (very basic heuristic)
        detected_language = "en"
        hindi_chars = any('\u0900' <= c <= '\u097f' for c in message)
        spanish_words = ["donde", "como", "dónde", "cómo", "ayuda", "baño"]
        arabic_chars = any('\u0600' <= c <= '\u06ff' for c in message)
        french_words = ["où", "comment", "toilettes", "aide", "bonjour"]
        portuguese_words = ["onde", "como", "banheiro", "ajuda", "obrigado"]

        if hindi_chars:
            detected_language = "hi"
        elif arabic_chars:
            detected_language = "ar"
        elif any(w in message_lower for w in spanish_words):
            detected_language = "es"
        elif any(w in message_lower for w in french_words):
            detected_language = "fr"
        elif any(w in message_lower for w in portuguese_words):
            detected_language = "pt"

        return IntentExtraction(
            detected_language=detected_language,
            intent=intent,
            is_emergency=is_emergency,
            start_location=start_location,
            end_location=end_location,
            facility_type=facility_type
        )

    def _mock_generate_response(
        self,
        message: str,
        detected_language: str,
        intent: str,
        navigation_context: Optional[str] = None,
        crowd_alert: Optional[str] = None
    ) -> str:
        """Friendly rule-based response when Gemini API is unavailable."""
        responses = {
            "en": {
                "greeting": "Hello! Welcome to the FIFA World Cup 2026! I'm Stadium Saathi, your personal stadium assistant. How can I help you today?",
                "navigation": f"I'd be happy to help you navigate! {navigation_context or 'Please tell me your current location and destination.'}",
                "facility_query": f"Let me find that for you! {navigation_context or 'Could you tell me your current location?'}",
                "emergency": "🚨 EMERGENCY: Please remain calm. Contact the nearest staff member or call security immediately. First aid stations are located at Gates A, C, and E.",
                "general_info": "Welcome to the FIFA World Cup 2026 stadium! I can help you find gates, food, washrooms, first aid, and navigate anywhere in the stadium. What do you need?",
            },
            "hi": {
                "greeting": "नमस्ते! FIFA विश्व कप 2026 में आपका स्वागत है! मैं Stadium Saathi हूँ। आप मुझसे हिंदी में बात कर सकते हैं।",
                "navigation": f"मैं आपको रास्ता बताने में मदद करूँगा! {navigation_context or 'कृपया अपना वर्तमान स्थान और गंतव्य बताएं।'}",
                "facility_query": f"मैं आपके लिए खोजता हूँ! {navigation_context or 'कृपया अपना वर्तमान स्थान बताएं।'}",
                "emergency": "🚨 आपातकाल: शांत रहें। निकटतम स्टाफ सदस्य से संपर्क करें।",
                "general_info": "FIFA विश्व कप 2026 स्टेडियम में आपका स्वागत है! मैं आपको गेट, खाना, वॉशरूम और प्राथमिक चिकित्सा खोजने में मदद कर सकता हूँ।",
            },
            "es": {
                "greeting": "¡Hola! ¡Bienvenido a la Copa Mundial FIFA 2026! Soy Stadium Saathi, tu asistente personal.",
                "navigation": f"¡Con gusto te ayudo a navegar! {navigation_context or 'Por favor dime tu ubicación actual y destino.'}",
                "facility_query": f"¡Déjame buscar eso! {navigation_context or '¿Puedes decirme tu ubicación actual?'}",
                "emergency": "🚨 EMERGENCIA: Mantén la calma. Contacta al personal más cercano o llama a seguridad.",
                "general_info": "¡Bienvenido al estadio de la Copa Mundial FIFA 2026! Puedo ayudarte a encontrar puertas, comida, baños y primeros auxilios.",
            },
        }

        lang_responses = responses.get(detected_language, responses["en"])
        base_response = lang_responses.get(intent, lang_responses["general_info"])

        if crowd_alert:
            if detected_language == "hi":
                base_response += f"\n\n⚠️ भीड़ चेतावनी: {crowd_alert}"
            elif detected_language == "es":
                base_response += f"\n\n⚠️ Alerta de aglomeración: {crowd_alert}"
            else:
                base_response += f"\n\n⚠️ Crowd Alert: {crowd_alert}"

        return base_response


# Singleton instance
gemini_service = GeminiService()

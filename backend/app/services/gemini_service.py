import os
import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.core.config import settings

# ----------------------------------------------------------------------------
# Pydantic schemas for Gemini structured outputs
# ----------------------------------------------------------------------------

class IntentExtraction(BaseModel):
    """
    Combined schema: extracts intent/entities AND (when possible) a ready-to-use
    friendly response in a single Gemini call. This cuts the number of API
    round-trips in half for non-navigation queries (greeting, general_info,
    emergency, other), which make up the majority of fan messages.

    For 'navigation' / 'facility_query' intents, `preliminary_response` is left
    empty because the final response must incorporate the computed route and
    crowd data, which are only known after this extraction step runs.
    """
    detected_language: str = Field(description="ISO 639-1 language code or full language name of the fan's message")
    intent: str = Field(description="Intent category: 'navigation', 'facility_query', 'general_info', 'emergency', 'greeting', or 'other'")
    is_emergency: bool = Field(description="True if this is an emergency like medical distress, security issue, fire, or danger")
    start_location: Optional[str] = Field(None, description="Extracted starting location name or ID if mentioned in the query")
    end_location: Optional[str] = Field(None, description="Extracted destination location name, type, or ID if mentioned in the query")
    facility_type: Optional[str] = Field(None, description="If looking for a facility type, extract one of: 'gate', 'section', 'food_stall', 'washroom', 'first_aid', 'escalator', 'exit'")
    preliminary_response: str = Field(
        default="",
        description=(
            "If the intent is 'navigation' or 'facility_query', leave this EMPTY "
            "(a follow-up call will generate the final response using computed route data). "
            "For ALL OTHER intents (greeting, general_info, emergency, other), provide a "
            "complete, friendly, ready-to-send response in the SAME language as the user's message."
        )
    )


class FinalResponse(BaseModel):
    response: str = Field(description="A friendly, helpful response in the SAME language the fan used.")
    is_emergency: bool = Field(description="True if an emergency is detected")


# Intents that require a second Gemini call because the response must
# incorporate route/crowd data that is only available after pathfinding.
_INTENTS_REQUIRING_CONTEXT_PASS = {"navigation", "facility_query"}


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None

        # Check if API key is valid and not placeholder
        if self.api_key and "your_gemini_api_key" not in self.api_key.lower():
            try:
                self.client = genai.Client(api_key=self.api_key)
                print("Gemini Client initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize Gemini Client: {e}")
        else:
            print("WARNING: Gemini API Key is missing or placeholder. Running in Mock Mode.")

    def is_mock_mode(self) -> bool:
        return self.client is None

    @staticmethod
    def needs_context_pass(intent: str) -> bool:
        """Whether this intent requires a second Gemini call with navigation/crowd context."""
        return intent in _INTENTS_REQUIRING_CONTEXT_PASS

    async def extract_intent(self, message: str) -> IntentExtraction:
        """
        Single combined call: extracts intent/language/entities AND (for
        non-navigation intents) a ready-to-use final response, in ONE
        round-trip to Gemini instead of two.
        """
        if self.is_mock_mode():
            return self._mock_extract_intent(message)

        prompt = f"""
        Analyze this user message from a stadium visitor at a FIFA World Cup 2026 match.
        Extract the language, core intent, start/end locations, and any facility type being searched for.

        Message: "{message}"
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=IntentExtraction,
                    system_instruction=(
                        "You are 'Stadium Saathi', an expert multilingual assistant for stadium inquiries at "
                        "FIFA World Cup 2026. Accurately categorize the user intent and extract locations. "
                        "Be conservative with emergencies: only set is_emergency=true if there is a medical "
                        "issue, security threat, fire, or immediate danger. "
                        "If the intent is 'navigation' or 'facility_query', leave preliminary_response empty. "
                        "For every other intent, write a warm, concise, ready-to-send preliminary_response "
                        "in the SAME language as the user's message."
                    )
                )
            )

            data = json.loads(response.text)
            return IntentExtraction(**data)
        except Exception as e:
            print(f"Gemini extract_intent error: {e}. Falling back to mock extraction.")
            return self._mock_extract_intent(message)

    async def generate_response(
        self,
        message: str,
        detected_language: str,
        intent: str,
        navigation_context: Optional[str] = None,
        crowd_alert: Optional[str] = None
    ) -> str:
        """
        Second-pass call, used ONLY for navigation/facility_query intents where
        the response must incorporate computed route + crowd data.
        """
        if self.is_mock_mode():
            return self._mock_generate_response(message, detected_language, intent, navigation_context, crowd_alert)

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
        4. If a crowd alert is provided, politely advise the user about the congestion and guide them to use the alternate path recommended in the navigation route info.
        5. If there is an emergency, instruct them to stay calm and inform them that stadium medical/security staff have been alerted and are on their way.
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instr
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini generate_response error: {e}. Falling back to mock response.")
            return self._mock_generate_response(message, detected_language, intent, navigation_context, crowd_alert)

    # ------------------------------------------------------------------------
    # Mock mode (used when no API key is configured, e.g. local dev/testing)
    # ------------------------------------------------------------------------

    def _mock_extract_intent(self, message: str) -> IntentExtraction:
        """Mock implementation of intent extraction for offline testing"""
        msg = message.lower()

        # Simple rule-based detector
        detected_lang = "English"
        if any(w in msg for w in ["hola", "como", "dónde", "baño", "puerta"]):
            detected_lang = "Spanish"
        elif any(w in msg for w in ["bonjour", "ou est", "toilette", "porte"]):
            detected_lang = "French"
        elif any(w in msg for w in ["hindi", "kahan", "rasta", "shauchalay", "gate"]):
            detected_lang = "Hindi"
        elif any(w in msg for w in ["marhaba", "ayn", "shukran", "bab"]):
            detected_lang = "Arabic"
        elif any(w in msg for w in ["olá", "onde", "banheiro", "porta"]):
            detected_lang = "Portuguese"

        is_emergency = any(w in msg for w in ["hurt", "help", "pain", "medical", "doctor", "police", "fight", "fire", "emergency", "accident", "bleeding", "choking"])

        intent = "general_info"
        facility_type = None
        end_location = None

        if is_emergency:
            intent = "emergency"
        elif any(w in msg for w in ["food", "eat", "stall", "burger", "pizza", "curry", "taco", "cafe"]):
            intent = "facility_query"
            facility_type = "food_stall"
            for food in ["burger", "taco", "curry", "cafe", "pizza", "halal"]:
                if food in msg:
                    end_location = food
        elif any(w in msg for w in ["toilet", "washroom", "bathroom", "restroom", "shauchalay", "baño", "banheiro", "toilette"]):
            intent = "facility_query"
            facility_type = "washroom"
        elif any(w in msg for w in ["first aid", "medical room", "doctor", "clinic", "aid"]):
            intent = "facility_query"
            facility_type = "first_aid"
        elif any(w in msg for w in ["gate", "entrance", "exit", "section", "escalator", "elevator", "stairs", "how to get", "go to", "directions", "route", "way to"]):
            intent = "navigation"
            if "section" in msg:
                facility_type = "section"
            elif "gate" in msg:
                facility_type = "gate"
            elif "escalator" in msg:
                facility_type = "escalator"

            for word in msg.split():
                if word.isdigit() or (word.startswith("gate_") or word.startswith("section_")):
                    end_location = word
        elif any(w in msg for w in ["hello", "hi", "hey", "hola", "namaste", "marhaba", "bonjour"]):
            intent = "greeting"

        start_location = None
        if "from" in msg:
            parts = msg.split("from")
            if len(parts) > 1:
                words = parts[1].strip().split()
                if words:
                    start_location = words[0]

        preliminary_response = ""
        if intent not in _INTENTS_REQUIRING_CONTEXT_PASS:
            preliminary_response = self._mock_generate_response(
                message=message,
                detected_language=detected_lang,
                intent=intent
            )

        return IntentExtraction(
            detected_language=detected_lang,
            intent=intent,
            is_emergency=is_emergency,
            start_location=start_location,
            end_location=end_location,
            facility_type=facility_type,
            preliminary_response=preliminary_response
        )

    def _mock_generate_response(
        self,
        message: str,
        detected_language: str,
        intent: str,
        navigation_context: Optional[str] = None,
        crowd_alert: Optional[str] = None
    ) -> str:
        """Mock implementation of response generation for offline testing"""
        lang = detected_language.lower()

        responses = {
            "english": {
                "greeting": "Hello! Welcome to the stadium. How can I help you today?",
                "emergency": "Emergency detected. Please stay calm. Stadium medical and security teams have been notified and are on their way to your area.",
                "general": "Thank you for asking. Please let me know if you need directions or facility details.",
                "nav_prefix": "Here are your directions: ",
                "crowd_prefix": "Notice: Some areas are congested. We have adjusted your route. "
            },
            "spanish": {
                "greeting": "¡Hola! Bienvenido al estadio. ¿Cómo puedo ayudarte hoy?",
                "emergency": "Emergencia detectada. Por favor, mantenga la calma. Los equipos médicos y de seguridad del estadio han sido notificados y están en camino a su área.",
                "general": "Gracias por preguntar. Por favor, avíseme si necesita direcciones o detalles de las instalaciones.",
                "nav_prefix": "Aquí están sus instrucciones de navegación: ",
                "crowd_prefix": "Aviso: Algunas áreas están congestionadas. Hemos ajustado su ruta. "
            },
            "hindi": {
                "greeting": "नमस्ते! स्टेडियम में आपका स्वागत है। आज मैं आपकी क्या सहायता कर सकता हूँ?",
                "emergency": "आपातकालीन स्थिति का पता चला है। कृपया शांत रहें। स्टेडियम की मेडिकल और सुरक्षा टीमों को सूचित कर दिया गया है और वे आपके क्षेत्र में आ रही हैं।",
                "general": "पूछने के लिए धन्यवाद। यदि आपको दिशा-निर्देश या सुविधाओं के विवरण की आवश्यकता हो तो कृपया मुझे बताएं।",
                "nav_prefix": "यहाँ आपके दिशा-निर्देश हैं: ",
                "crowd_prefix": "सूचना: कुछ क्षेत्रों में भीड़ है। हमने आपका मार्ग बदल दिया है। "
            },
            "french": {
                "greeting": "Bonjour! Bienvenue au stade. Comment puis-je vous aider aujourd'hui?",
                "emergency": "Urgence détectée. Veuillez rester calme. Les équipes médicales et de sécurité du stade ont été informées et sont en route vers votre zone.",
                "general": "Merci de demander. Veuillez me faire savoir si vous avez besoin d'itinéraires ou de détails sur les installations.",
                "nav_prefix": "Voici vos directions: ",
                "crowd_prefix": "Avis: Certaines zones sont encombrées. Nous avons adapté votre itinéraire. "
            },
            "arabic": {
                "greeting": "مرحباً! أهلاً بك في الملعب. كيف يمكنني مساعدتك اليوم؟",
                "emergency": "تم اكتشاف حالة طوارئ. يرجى البقاء هادئاً. تم إخطار الفرق الطبية والأمنية في الملعب وهي في طريقها إلى منطقتك.",
                "general": "شكراً لسؤالك. يرجى إعلامي إذا كنت بحاجة إلى اتجاهات أو تفاصيل عن المرافق.",
                "nav_prefix": "إليك الاتجاهات: ",
                "crowd_prefix": "تنبيه: بعض المناطق مزدحمة. لقد قمنا بتعديل مسارك. "
            },
            "portuguese": {
                "greeting": "Olá! Bem-vindo ao estádio. Como posso ajudar você hoje?",
                "emergency": "Emergência detectada. Por favor, mantenha a calma. As equipes médicas e de segurança do estádio foram notificadas e estão a caminho da sua área.",
                "general": "Obrigado por perguntar. Por favor, informe-me se precisar de direções ou detalhes das instalações.",
                "nav_prefix": "Aqui estão as suas direções: ",
                "crowd_prefix": "Aviso: Algumas áreas estão congestionadas. Ajustamos a sua rota. "
            }
        }

        lang_key = "english"
        for k in responses.keys():
            if k in lang:
                lang_key = k
                break

        r = responses[lang_key]

        if intent == "greeting":
            return r["greeting"]
        elif intent == "emergency":
            return r["emergency"]
        elif intent in ["navigation", "facility_query"]:
            resp = ""
            if crowd_alert:
                resp += r["crowd_prefix"]
            if navigation_context:
                resp += r["nav_prefix"] + navigation_context
            else:
                resp += "I couldn't calculate a route because the start or destination location is not clear. Could you please specify where you are and where you want to go?"
            return resp
        else:
            return r["general"]


gemini_service = GeminiService()

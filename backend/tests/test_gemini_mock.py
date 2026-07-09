import pytest
from app.services.gemini_service import GeminiService


@pytest.fixture
def mock_service():
    """
    Force a fresh GeminiService instance in mock mode regardless of whether
    a real GEMINI_API_KEY is set in the test environment, so these tests
    are deterministic in CI.
    """
    svc = GeminiService()
    svc.client = None  # force mock mode
    assert svc.is_mock_mode() is True
    return svc


class TestMockIntentExtraction:
    @pytest.mark.asyncio
    async def test_emergency_keyword_sets_is_emergency(self, mock_service):
        result = await mock_service.extract_intent("help please I am bleeding")
        assert result.is_emergency is True
        assert result.intent == "emergency"

    @pytest.mark.asyncio
    async def test_non_emergency_message_not_flagged(self, mock_service):
        result = await mock_service.extract_intent("where can I get a burger")
        assert result.is_emergency is False

    @pytest.mark.asyncio
    async def test_washroom_query_maps_to_facility_query(self, mock_service):
        result = await mock_service.extract_intent("where is the nearest washroom")
        assert result.intent == "facility_query"
        assert result.facility_type == "washroom"

    @pytest.mark.asyncio
    async def test_navigation_query_maps_to_navigation_intent(self, mock_service):
        result = await mock_service.extract_intent("how do I get to gate 3")
        assert result.intent == "navigation"

    @pytest.mark.asyncio
    async def test_greeting_detected(self, mock_service):
        result = await mock_service.extract_intent("hello there")
        assert result.intent == "greeting"

    @pytest.mark.asyncio
    async def test_spanish_keyword_detected(self, mock_service):
        result = await mock_service.extract_intent("hola, donde esta el baño")
        assert result.detected_language == "Spanish"

    @pytest.mark.asyncio
    async def test_default_language_is_english(self, mock_service):
        result = await mock_service.extract_intent("what time does the match start")
        assert result.detected_language == "English"

    @pytest.mark.asyncio
    async def test_emergency_keyword_overrides_facility_keyword(self, mock_service):
        """
        A message that mentions both a facility word ('food') and an
        emergency word ('help') must be classified as emergency, since
        the medical/safety branch should take priority.
        """
        result = await mock_service.extract_intent("help, my friend collapsed near the food stall")
        assert result.intent == "emergency"
        assert result.is_emergency is True


class TestMockResponseGeneration:
    @pytest.mark.asyncio
    async def test_emergency_response_in_requested_language(self, mock_service):
        response = await mock_service.generate_response(
            message="help",
            detected_language="Hindi",
            intent="emergency",
        )
        assert "आपातकालीन" in response or len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_unsupported_language_falls_back_to_english(self, mock_service):
        response = await mock_service.generate_response(
            message="hello",
            detected_language="Klingon",
            intent="greeting",
        )
        assert response == "Hello! Welcome to the stadium. How can I help you today?"

    @pytest.mark.asyncio
    async def test_navigation_without_context_asks_for_clarification(self, mock_service):
        response = await mock_service.generate_response(
            message="take me somewhere",
            detected_language="English",
            intent="navigation",
            navigation_context=None,
        )
        assert "clear" in response.lower() or "specify" in response.lower()

    @pytest.mark.asyncio
    async def test_navigation_with_context_includes_directions(self, mock_service):
        response = await mock_service.generate_response(
            message="take me to section 101",
            detected_language="English",
            intent="navigation",
            navigation_context="Gate A -> Section 101",
        )
        assert "Gate A -> Section 101" in response

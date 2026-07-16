from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ✅ IMPROVEMENT: Added Field validators for min/max length + whitespace stripping
class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The visitor's message (1–500 characters)"
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique session identifier for the conversation"
    )
    current_location_id: Optional[str] = Field(
        None,
        max_length=50,
        description="Optional current location ID for navigation context"
    )

    # ✅ IMPROVEMENT: Strip whitespace and reject blank-only messages
    @field_validator("message")
    @classmethod
    def strip_and_validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or whitespace only")
        return stripped

    @field_validator("session_id")
    @classmethod
    def strip_session_id(cls, v: str) -> str:
        return v.strip()


class NavigationStep(BaseModel):
    instruction: str
    location_id: str
    level: int
    zone: str


class ChatResponse(BaseModel):
    response: str
    detected_language: str
    intent: str
    is_emergency: bool
    navigation_steps: Optional[List[NavigationStep]] = None
    crowd_alert: Optional[str] = None


# ── Dashboard models ────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class FrequentQuery(BaseModel):
    query_type: str
    count: int


class EmergencyLog(BaseModel):
    id: int
    session_id: str
    fan_message: str
    timestamp: datetime


class DashboardStats(BaseModel):
    total_chats: int
    emergency_count: int
    language_breakdown: Dict[str, int]
    intent_breakdown: Dict[str, int]
    frequent_queries: List[FrequentQuery]
    recent_emergencies: List[EmergencyLog]

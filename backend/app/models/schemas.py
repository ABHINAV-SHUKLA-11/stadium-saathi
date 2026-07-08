from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    session_id: str
    current_location_id: Optional[str] = None

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

class CrowdDensitySnapshot(BaseModel):
    zone_id: str
    density: int
    status: str # Low, Medium, High, Critical
    recorded_at: datetime

    class Config:
        from_attributes = True

class FrequentQuery(BaseModel):
    intent: str
    count: int

class EmergencyLog(BaseModel):
    id: int
    session_id: str
    fan_message: str
    ai_response: str
    detected_language: str
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_queries: int
    active_sessions: int
    emergency_count: int
    language_breakdown: Dict[str, int]

class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None

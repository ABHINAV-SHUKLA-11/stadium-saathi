from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import DashboardStats, FrequentQuery, EmergencyLog, LoginRequest, LoginResponse
from app.services.chat_service import chat_service
from typing import List, Optional

router = APIRouter()

async def verify_admin(authorization: Optional[str] = Header(None)):
    """Verifies that the request contains the correct password in the Authorization header"""
    expected_token = f"Bearer {settings.DASHBOARD_PASSWORD}"
    if not authorization or authorization != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Access denied: Invalid or missing administration credentials."
        )
    return True

@router.post("/login", response_model=LoginResponse)
async def login_dashboard(request: LoginRequest):
    """Simple password verification gate for dashboard login"""
    if request.password == settings.DASHBOARD_PASSWORD:
        return LoginResponse(
            success=True,
            token=settings.DASHBOARD_PASSWORD, # Simply use the password as the token for MVP simplicity
            message="Authenticated successfully."
        )
    return LoginResponse(
        success=False,
        message="Invalid password. Access denied."
    )

@router.get("/stats", response_model=DashboardStats, dependencies=[Depends(verify_admin)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Retrieve aggregate stats for the dashboard panels"""
    stats = await chat_service.get_dashboard_stats(db)
    return stats

@router.get("/frequent-queries", response_model=List[FrequentQuery], dependencies=[Depends(verify_admin)])
async def get_frequent_queries(db: AsyncSession = Depends(get_db)):
    """Retrieve top fan query categories"""
    frequent = await chat_service.get_frequent_queries(db)
    return frequent

@router.get("/emergencies", response_model=List[EmergencyLog], dependencies=[Depends(verify_admin)])
async def get_emergencies(db: AsyncSession = Depends(get_db)):
    """Retrieve recent queries flagged as emergency"""
    emergencies = await chat_service.get_emergency_logs(db)
    return emergencies

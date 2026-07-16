import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import DashboardStats, FrequentQuery, EmergencyLog, LoginRequest, LoginResponse
from app.services.chat_service import chat_service
from typing import List, Optional

# ✅ IMPROVEMENT: Rate limiting on login endpoint
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


async def verify_admin(authorization: Optional[str] = Header(None)):
    """Verifies that the request contains the correct password in the Authorization header."""
    expected_token = f"Bearer {settings.DASHBOARD_PASSWORD}"
    if not authorization or authorization != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Access denied: Invalid or missing administration credentials."
        )
    return True


# ✅ IMPROVEMENT: Rate limiting — max 5 login attempts per minute per IP
@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login_dashboard(request: Request, credentials: LoginRequest):
    """Simple password verification gate for dashboard login."""
    if credentials.password == settings.DASHBOARD_PASSWORD:
        logger.info("Dashboard login successful from %s", request.client.host)
        return LoginResponse(
            success=True,
            token=f"Bearer {settings.DASHBOARD_PASSWORD}",
            message="Login successful"
        )
    else:
        logger.warning("Failed dashboard login attempt from %s", request.client.host)
        raise HTTPException(status_code=401, detail="Invalid password.")


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """Returns aggregate statistics for the staff dashboard."""
    stats = await chat_service.get_dashboard_stats(db)
    return stats


@router.get("/emergencies", response_model=List[EmergencyLog])
async def get_recent_emergencies(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """Returns the most recent emergency chat entries."""
    emergencies = await chat_service.get_recent_emergencies(db)
    return emergencies


@router.get("/frequent-queries", response_model=List[FrequentQuery])
async def get_frequent_queries(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """Returns the most frequently asked query types."""
    queries = await chat_service.get_frequent_queries(db)
    return queries

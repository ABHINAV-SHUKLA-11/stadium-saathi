import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware  # ✅ IMPROVEMENT: Gzip compression
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy import select, func

# ✅ IMPROVEMENT: Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db, async_session_factory
from app.models.models import StadiumLocation
from app.services.crowd_service import crowd_service
from app.routers import chat, crowd, dashboard

# ✅ IMPROVEMENT: Configure structured logging instead of bare print()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ✅ IMPROVEMENT: Create rate limiter singleton (used by routers too)
limiter = Limiter(key_func=get_remote_address)


async def auto_seed_database():
    """Checks if database is seeded and seeds it from stadium_layout.json if empty."""
    async with async_session_factory() as session:
        try:
            query = select(func.count(StadiumLocation.id))
            result = await session.execute(query)
            count = result.scalar() or 0

            if count == 0:
                logger.info("Database is empty. Starting auto-seeding...")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                layout_path = os.path.join(current_dir, "data", "stadium_layout.json")

                if os.path.exists(layout_path):
                    with open(layout_path, "r") as f:
                        data = json.load(f)

                    for loc_data in data["locations"]:
                        loc = StadiumLocation(
                            id=loc_data["id"],
                            name=loc_data["name"],
                            type=loc_data["type"],
                            zone=loc_data.get("zone", ""),
                            description=loc_data.get("description", ""),
                            level=loc_data.get("level", 0),
                            nearby_ids=json.dumps(loc_data.get("nearby_ids", [])),
                            x_coord=loc_data.get("x_coord"),
                            y_coord=loc_data.get("y_coord"),
                        )
                        session.add(loc)

                    await session.commit()
                    logger.info("Auto-seeding complete.")
                else:
                    logger.warning("stadium_layout.json not found at: %s", layout_path)
            else:
                logger.info("Database already seeded with %d locations.", count)

        except Exception as e:
            logger.error("Auto-seeding failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: runs startup tasks before serving, cleanup on shutdown."""
    logger.info("Stadium Saathi API starting up...")
    await init_db()
    await auto_seed_database()
    crowd_service.start_simulation()
    logger.info("Crowd simulation started. Ready to serve requests.")
    yield
    logger.info("Stadium Saathi API shutting down...")
    crowd_service.stop_simulation()


# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stadium Saathi API",
    description="Multilingual assistant and crowd management API for World Cup 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# ✅ IMPROVEMENT: Register rate limiter on app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ✅ IMPROVEMENT: GZip compression (saves bandwidth, improves load times)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(crowd.router, prefix="/api/crowd", tags=["Crowd"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# ── Static files (frontend) ───────────────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

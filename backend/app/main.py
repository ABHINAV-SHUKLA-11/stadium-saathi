import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import init_db, async_session_factory
from app.models.models import StadiumLocation
from app.services.crowd_service import crowd_service
from app.routers import chat, crowd, dashboard

async def auto_seed_database():
    """Checks if database is seeded and seeds it from stadium_layout.json if empty"""
    async with async_session_factory() as session:
        try:
            # Check if locations exist
            query = select(func.count(StadiumLocation.id))
            result = await session.execute(query)
            count = result.scalar() or 0
            
            if count == 0:
                print("Database is empty. Starting auto-seeding...")
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
                            level=loc_data["level"],
                            zone=loc_data["zone"],
                            x=loc_data["x"],
                            y=loc_data["y"],
                            nearby_ids=",".join(loc_data["nearby_ids"]),
                            description=loc_data.get("description", ""),
                            metadata_json=json.dumps(loc_data.get("metadata", {}))
                        )
                        session.add(loc)
                    await session.commit()
                    print(f"Auto-seeded {len(data['locations'])} stadium locations successfully.")
                else:
                    print(f"Error: layout file not found at {layout_path}")
            else:
                print(f"Database already contains {count} locations. Skipping seeding.")
        except Exception as e:
            print(f"Failed to auto-seed database: {e}")
            await session.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Initializing database...")
    await init_db()
    
    print("Checking database seeding...")
    await auto_seed_database()
    
    print("Starting crowd simulation service...")
    await crowd_service.start_simulation()
    
    yield
    
    # Shutdown actions
    print("Stopping crowd simulation service...")
    await crowd_service.stop_simulation()

app = FastAPI(
    title="Stadium Saathi API",
    description="Multilingual assistant and crowd management API for World Cup 2026",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(crowd.router, prefix="/api/crowd", tags=["Crowd"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "gemini_status": "Mock Mode" if settings.GEMINI_API_KEY == "" else "API Configured"
    }

# Mount frontend build static files in production if available
# This allows serving the React build from the same FastAPI server
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    print(f"Serving static files from: {static_dir}")
else:
    print(f"Static directory not found at: {static_dir}. Running API-only server.")

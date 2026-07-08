import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory
from app.models.models import CrowdDensity

# Configure logging
logger = logging.getLogger("crowd_service")

# Fictional Stadium Zones
ZONES = [
    "North", "South", "East", "West", 
    "North-East", "South-West", "North-West", "South-East", 
    "Center"
]

class CrowdService:
    def __init__(self):
        # Initialize baseline densities between 20% and 60%
        self.current_densities: Dict[str, int] = {zone: random.randint(20, 60) for zone in ZONES}
        self.listeners: List[asyncio.Queue] = []
        self.is_running = False
        self._simulation_task = None

    def get_current_densities(self) -> Dict[str, int]:
        return self.current_densities

    async def register_listener(self) -> asyncio.Queue:
        """Register a new listener queue for SSE updates"""
        queue = asyncio.Queue()
        self.listeners.append(queue)
        # Immediately push current state to the new listener
        await queue.put(self.current_densities)
        return queue

    def unregister_listener(self, queue: asyncio.Queue):
        if queue in self.listeners:
            self.listeners.remove(queue)

    async def start_simulation(self):
        self.is_running = True
        self._simulation_task = asyncio.create_task(self._run_simulation())
        logger.info("Crowd Simulation Service started.")

    async def stop_simulation(self):
        self.is_running = False
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
        logger.info("Crowd Simulation Service stopped.")

    async def _run_simulation(self):
        while self.is_running:
            try:
                # Update densities using random walk (clamped between 10% and 98%)
                for zone in ZONES:
                    current = self.current_densities[zone]
                    # Random change between -15 and +15
                    change = random.randint(-15, 15)
                    
                    # Periodic spikes (10% chance) to simulate rush hours / mass movement
                    if random.random() < 0.1:
                        change = random.choice([30, -30])
                        
                    new_density = max(10, min(98, current + change))
                    self.current_densities[zone] = new_density

                # Save snapshot to database
                await self._save_snapshot_to_db()

                # Notify all SSE listeners
                # We duplicate list to avoid modification during iteration
                active_listeners = list(self.listeners)
                for queue in active_listeners:
                    try:
                        await queue.put(self.current_densities)
                    except Exception as e:
                        # Listener queue might be closed/full
                        self.listeners.remove(queue)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in crowd simulation loop: {e}")
                
            # Run every 8-12 seconds
            await asyncio.sleep(random.uniform(8.0, 12.0))

    async def _save_snapshot_to_db(self):
        """Save the current crowd density snapshot to SQLite database"""
        async with async_session_factory() as session:
            try:
                for zone, density in self.current_densities.items():
                    log_entry = CrowdDensity(
                        zone_id=zone,
                        density=density
                    )
                    session.add(log_entry)
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to save crowd snapshot to DB: {e}")
                await session.rollback()

crowd_service = CrowdService()

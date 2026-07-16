from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.crowd_service import crowd_service
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_densities(densities: dict) -> list:
    """Convert raw density dict into formatted list with status labels."""
    formatted = []
    for zone, density in densities.items():
        if density > 90:
            status = "Critical"
        elif density > 75:
            status = "High"
        elif density > 40:
            status = "Medium"
        else:
            status = "Low"

        formatted.append({
            "zone": zone,
            "density": density,
            "status": status,
        })
    return formatted


@router.get("")
async def get_crowd_densities():
    """Get current snapshot of crowd densities for all zones."""
    densities = crowd_service.get_current_densities()
    return _format_densities(densities)


@router.get("/stream")
async def stream_crowd_densities():
    """SSE endpoint for streaming real-time crowd updates to the dashboard."""

    async def event_generator():
        queue = await crowd_service.register_listener()
        last_sent = None  # ✅ IMPROVEMENT: Track last sent data

        try:
            while True:
                try:
                    # ✅ IMPROVEMENT: Timeout after 30s and send heartbeat
                    # so Nginx / load-balancers don't close the connection
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # ✅ IMPROVEMENT: Only push if data has actually changed
                    if data != last_sent:
                        last_sent = data
                        formatted = _format_densities(data)
                        yield f"data: {json.dumps(formatted)}\n\n"

                except asyncio.TimeoutError:
                    # Send a keepalive comment so the connection stays open
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected — cleaning up listener.")
        finally:
            crowd_service.unregister_listener(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering for SSE
        }
    )

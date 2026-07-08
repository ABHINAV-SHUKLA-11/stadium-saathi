from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.crowd_service import crowd_service
import json
import asyncio

router = APIRouter()

@router.get("")
async def get_crowd_densities():
    """Get current snapshot of crowd densities for all zones"""
    densities = crowd_service.get_current_densities()
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
            "zone_id": zone,
            "density": density,
            "status": status
        })
    return formatted

@router.get("/stream")
async def stream_crowd_densities():
    """SSE endpoint for streaming real-time crowd updates to the dashboard"""
    async def event_generator():
        queue = await crowd_service.register_listener()
        try:
            while True:
                data = await queue.get()
                # Format each update as a JSON-encoded string
                formatted_data = []
                for zone, density in data.items():
                    if density > 90:
                        status = "Critical"
                    elif density > 75:
                        status = "High"
                    elif density > 40:
                        status = "Medium"
                    else:
                        status = "Low"
                    formatted_data.append({
                        "zone_id": zone,
                        "density": density,
                        "status": status
                    })
                yield f"data: {json.dumps(formatted_data)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            crowd_service.unregister_listener(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

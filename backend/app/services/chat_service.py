from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, NavigationStep
from app.services.gemini_service import gemini_service
from app.services.navigation_service import navigation_service
from app.services.crowd_service import crowd_service
from app.services.chat_service import chat_service
from typing import List, Optional

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Main endpoint for visitor chat queries.

    Efficiency note: this endpoint makes AT MOST 2 Gemini calls, and only 1 for
    the majority of messages. The first call (extract_intent) both classifies
    the intent AND generates a ready-to-use response in the same pass. A
    second call (generate_response) is only made for 'navigation' /
    'facility_query' intents, since those responses must incorporate the
    computed route + crowd data that only exists after pathfinding runs.
    """
    message = request.message
    session_id = request.session_id
    current_loc_id = request.current_location_id

    # 1. Single combined Gemini call: intent + entities + (when possible) response
    extracted = await gemini_service.extract_intent(message)

    intent = extracted.intent
    detected_language = extracted.detected_language
    is_emergency = extracted.is_emergency

    navigation_steps = None
    navigation_context = None
    crowd_alert = None

    # 2. Check if intent is navigation or facility query
    if intent in ["navigation", "facility_query"] and not is_emergency:
        # Determine starting location
        start_node = None
        if extracted.start_location:
            matched_start = navigation_service.fuzzy_match_location(extracted.start_location)
            if matched_start:
                start_node = matched_start["id"]

        if not start_node and current_loc_id:
            matched_start = navigation_service.get_location(current_loc_id)
            if matched_start:
                start_node = matched_start["id"]

        # If no starting location is known, default to Gate A
        if not start_node:
            start_node = "gate_a"

        # Determine destination node
        dest_node = None
        if intent == "facility_query" and extracted.facility_type:
            dest_node = navigation_service.find_nearest_facility(
                start_id=start_node,
                facility_type=extracted.facility_type
            )
        elif extracted.end_location:
            matched_dest = navigation_service.fuzzy_match_location(extracted.end_location)
            if matched_dest:
                dest_node = matched_dest["id"]

        # Run pathfinding if we have start & destination
        if start_node and dest_node and start_node != dest_node:
            current_crowd = crowd_service.get_current_densities()

            path = navigation_service.get_directions(start_node, dest_node, current_crowd)

            if path:
                formatted_steps = navigation_service.format_directions_steps(path)
                navigation_context = " -> ".join([loc["name"] for loc in path])
                navigation_context += f". Step-by-step: {'; '.join(formatted_steps)}"

                high_crowd_zones_traversed = []
                for loc in path:
                    zone = loc["zone"]
                    density = current_crowd.get(zone, 0)
                    if density > 75 and zone not in high_crowd_zones_traversed:
                        high_crowd_zones_traversed.append(zone)

                if high_crowd_zones_traversed:
                    crowd_alert = f"Note: The route passes through the {', '.join(high_crowd_zones_traversed)} zone(s), which are currently very crowded. We have adjusted your path to avoid the highest congestion."
                    navigation_context += f" Crowd congestion warning: {crowd_alert}"

                navigation_steps = [
                    NavigationStep(
                        instruction=inst,
                        location_id=loc["id"],
                        level=loc["level"],
                        zone=loc["zone"]
                    ) for inst, loc in zip(formatted_steps, path[1:])
                ]
            else:
                navigation_context = "Pathfinding failed. Start and end are disconnected or invalid."
        elif start_node == dest_node:
            navigation_context = "You are already at your destination."
        else:
            navigation_context = f"Unable to find the destination or facility type matching '{extracted.end_location or extracted.facility_type}'."

    # 3. Generate final response.
    #    - navigation/facility_query: needs a second Gemini call to weave in route + crowd context.
    #    - everything else: reuse the response already generated in step 1 (no extra API call).
    if gemini_service.needs_context_pass(intent):
        ai_response = await gemini_service.generate_response(
            message=message,
            detected_language=detected_language,
            intent=intent,
            navigation_context=navigation_context,
            crowd_alert=crowd_alert
        )
    else:
        ai_response = extracted.preliminary_response or await gemini_service.generate_response(
            message=message,
            detected_language=detected_language,
            intent=intent
        )

    # 4. Save chat entry to DB
    await chat_service.log_chat(
        db=db,
        session_id=session_id,
        fan_message=message,
        ai_response=ai_response,
        detected_language=detected_language,
        intent=intent,
        is_emergency=is_emergency
    )

    # 5. Build response object
    return ChatResponse(
        response=ai_response,
        detected_language=detected_language,
        intent=intent,
        is_emergency=is_emergency,
        navigation_steps=navigation_steps,
        crowd_alert=crowd_alert
    )

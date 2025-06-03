from fastapi import APIRouter
from ..core.state import processing_state
import os

router = APIRouter(tags=["Progress"])

@router.get("/progress")
async def get_progress():
    return {
        "progress": processing_state["progress"],
        "status": processing_state["status"],
        "logs": processing_state["logs"][-50:],
        "running": processing_state["running"],
        "combined_log": os.path.basename(processing_state["combined_log"]) if processing_state.get("combined_log") else "",
        "unmatched_values": os.path.basename(processing_state["unmatched_values"]) if processing_state.get("unmatched_values") else ""
    }

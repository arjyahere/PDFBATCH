from fastapi import APIRouter
from ..core.state import processing_state

router = APIRouter(tags=["Controls"])

@router.post("/pause")
async def pause_processing():
    processing_state["paused"] = True
    processing_state["status"] = "Paused"
    return {"message": "Processing paused"}

@router.post("/resume")
async def resume_processing():
    processing_state["paused"] = False
    processing_state["status"] = "Resumed"
    return {"message": "Processing resumed"}

@router.post("/stop")
async def stop_processing():
    processing_state["running"] = False
    processing_state["paused"] = False
    processing_state["status"] = "Stopped"
    return {"message": "Processing stopped"}

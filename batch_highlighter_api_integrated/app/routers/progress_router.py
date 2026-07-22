from typing import List
import os
from fastapi import APIRouter, Query

from ..schemas import ProcessingStatus
from ..core import get_logger, processing_state, state_lock, get_job_state
from ..config.settings import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/progress", tags=["Progress"])

OUTPUT_FOLDER = "output"


def list_output_files(dest_folder: str):
    """List all output files in the destination folder."""
    if dest_folder and dest_folder.strip():
        # If it's an absolute path, use it directly
        if os.path.isabs(dest_folder):
            dest = dest_folder
        # If it's a relative path that's not just 'output', join with OUTPUT_FOLDER
        elif dest_folder != OUTPUT_FOLDER:
            dest = os.path.join(OUTPUT_FOLDER, dest_folder)
        else:
            dest = OUTPUT_FOLDER
    else:
        dest = OUTPUT_FOLDER
    
    if not os.path.exists(dest):
        return []
    
    files = []
    for f in os.listdir(dest):
        file_path = os.path.join(dest, f)
        if os.path.isfile(file_path):
            files.append({
                "name": f,
                "type": "pdf" if f.endswith('.pdf') else "csv" if f.endswith('.csv') else "other"
            })
    return files


@router.get("", response_model=ProcessingStatus, summary="Get detailed progress")
async def get_progress(job_id: str = Query(None, description="Optional job ID for concurrent job tracking")):
    """Get detailed progress with optional job-specific state."""
    if job_id:
        # Return job-specific state
        state = await get_job_state(job_id)
        async with state_lock:
            output_files = [
                {"name": f, "type": "pdf" if f.endswith('.pdf') else "csv" if f.endswith('.csv') else "other"}
                for f in state.current_job_pdfs
            ]
            return ProcessingStatus(
                running=state.running,
                paused=state.paused,
                progress=state.progress,
                status=state.status,
                job_id=state.job_id,
                start_time=state.start_time,
                end_time=state.end_time,
                completed=state.completed,
                current_file=state.current_file,
                files_processed=state.files_processed,
                total_matches_found=state.total_matches_found,
                completion_summary=state.completion_summary,
                logs=state.logs,
                combined_log=state.combined_log or "",
                not_found_report=state.not_found_report or "",
                output_files=output_files
            )
    
    # Fallback to global state for backward compatibility
    async with state_lock:
        output_files = [
            {"name": f, "type": "pdf" if f.endswith('.pdf') else "csv" if f.endswith('.csv') else "other"}
            for f in processing_state.current_job_pdfs
        ]
        state = {
            "running": processing_state.running,
            "paused": processing_state.paused,
            "progress": processing_state.progress,
            "status": processing_state.status,
            "job_id": processing_state.job_id,
            "start_time": processing_state.start_time,
            "end_time": processing_state.end_time,
            "completed": processing_state.completed,
            "current_file": processing_state.current_file,
            "files_processed": processing_state.files_processed,
            "total_matches_found": processing_state.total_matches_found,
            "completion_summary": processing_state.completion_summary,
            "logs": processing_state.logs,
            "combined_log": processing_state.combined_log or "",
            "not_found_report": processing_state.not_found_report or "",
            "output_files": output_files
        }
    return ProcessingStatus(**state)


@router.get("/logs", response_model=List[dict], summary="Get processing logs")
async def get_logs(job_id: str = Query(None, description="Optional job ID for concurrent job tracking"), limit: int = 5000):
    """Get all processing logs with optional job-specific tracking."""
    if job_id:
        state = await get_job_state(job_id)
        async with state_lock:
            return state.logs[-limit:]
    
    async with state_lock:
        return processing_state.logs[-limit:]


__all__ = ["router"]

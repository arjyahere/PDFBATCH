"""
Process router with concurrent job queue support.
"""
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException

from ..schemas import ProcessResponse, ErrorDetail, JobStatusResponse
from ..core import get_logger, ValidationException, FileException, FilePermissionException
from ..core.state import COLOR_PRESETS
from ..services.job_queue import get_job_queue, create_job

logger = get_logger(__name__)
router = APIRouter(prefix="/process", tags=["Process"])

INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"


async def save_uploaded_file(upload_file: UploadFile, job_id: str) -> str:
    """Save uploaded file to input folder."""
    import os
    
    # Ensure input folder exists
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    
    # Get original filename
    original_name = upload_file.filename
    
    # Create clean filename without prefix
    temp_path = os.path.join(INPUT_FOLDER, f"{job_id}_{original_name}")
    logger.info(f"Saving uploaded file to: {os.path.abspath(temp_path)}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        logger.info(f"File saved successfully, size: {os.path.getsize(temp_path)} bytes")
        return temp_path
    except PermissionError:
        raise FilePermissionException(file_path=temp_path, detail="Permission denied")
    except Exception as e:
        raise FileException(file_path=temp_path, detail=f"Failed to save: {e}", code="FILE_SAVE_ERROR")


def load_data_file(data_path: str) -> pd.DataFrame:
    """Load data from CSV or Excel."""
    try:
        if data_path.lower().endswith(".csv"):
            df = pd.read_csv(data_path, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(data_path, dtype=str)
        # Ensure all values are strings (handle NaN from Excel)
        df = df.fillna('')
        return df
    except Exception as e:
        raise FileException(file_path=data_path, detail=f"Failed to read: {e}", code="DATA_READ_ERROR")


def validate_columns(df: pd.DataFrame, columns_str: str) -> List[str]:
    """Validate selected columns exist in data."""
    columns = [c.strip() for c in columns_str.split(',') if c.strip()]
    if not 1 <= len(columns) <= 2:
        raise ValidationException(detail="1 or 2 columns required", code="INVALID_COLUMNS", field="selected_columns")
    for col in columns:
        if col not in df.columns:
            raise ValidationException(detail=f"Column '{col}' not found", code="COLUMN_NOT_FOUND", field=col)
    return columns


def extract_values(df: pd.DataFrame, columns: List[str]):
    """Extract values from dataframe."""
    if len(columns) == 1:
        values = []
        for v in df[columns[0]]:
            if pd.isna(v):
                continue
            v_str = str(v).strip()
            if v_str and v_str.lower() != "nan":
                values.append(v_str)
        return values, None
    else:
        pairs = []
        for _, row in df.iterrows():
            v1_raw = row[columns[0]]
            v2_raw = row[columns[1]]
            if pd.isna(v1_raw) or pd.isna(v2_raw):
                continue
            v1 = str(v1_raw).strip()
            v2 = str(v2_raw).strip()
            if v1 and v1.lower() != "nan" and v2 and v2.lower() != "nan":
                pairs.append((v1, v2))
        return None, pairs


async def run_background_processing(data_temp: str, file_paths: List[str], columns: str, color: str, dest_folder: Optional[str], job_id: str):
    """Background task to submit job to queue."""
    try:
        df = load_data_file(data_temp)
        columns_list = [c.strip() for c in columns.split(',') if c.strip()]
        vals, pairs = extract_values(df, columns_list)
        values = vals if vals else pairs
        
        # Validate color
        if color not in COLOR_PRESETS:
            color = "Yellow"
        
        # Create job data
        job_data = {
            "files": [{"path": fp} for fp in file_paths],
            "columns": columns,
            "color": color,
            "dest_folder": dest_folder,
            "values": values
        }
        
        queue = get_job_queue()
        job = create_job(job_data, job_id=job_id)
        
        await queue.enqueue(job)
        
        logger.info(f"Job {job_id} submitted to queue")
    
    except Exception as e:
        logger.error(f"Failed to submit job {job_id}: {type(e).__name__}: {e}", exc_info=True)


@router.post("", response_model=ProcessResponse, responses={400: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}, summary="Start batch processing")
async def process_files(background_tasks: BackgroundTasks, data_file: UploadFile = File(...), documents: List[UploadFile] = File(...), selected_columns: str = Form(...), selected_color: str = Form("Yellow"), destination_folder: Optional[str] = Form(None)):
    """Start batch document highlighting process."""
    job_id = str(uuid.uuid4())
    
    try:
        # Save files
        data_temp = await save_uploaded_file(data_file, job_id)
        file_paths = []
        for doc in documents:
            fp = await save_uploaded_file(doc, job_id)
            file_paths.append(fp)
        
        # Validate columns
        df = load_data_file(data_temp)
        columns = validate_columns(df, selected_columns)
        vals, pairs = extract_values(df, columns)
        
        # Start background processing
        background_tasks.add_task(run_background_processing, data_temp, file_paths, selected_columns, selected_color, destination_folder, job_id)
        
        return ProcessResponse(
            message="Processing started",
            job_id=job_id,
            total_values=len(vals) if vals else None,
            total_pairs=len(pairs) if pairs else None,
            total_files=len(documents),
            progress_url="/api/v1/progress",
            links={"progress": "/api/v1/progress", "jobs": "/api/v1/process"}
        )
    
    except (ValidationException, FileException) as e:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})


@router.get("/{job_id}", response_model=JobStatusResponse, summary="Get job status")
async def get_job_status(job_id: str):
    """Get status of a processing job."""
    queue = get_job_queue()
    job = await queue.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"})
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result=job.result,
        error=job.error
    )


@router.get("", response_model=List[JobStatusResponse], summary="List all jobs")
async def list_jobs():
    """List all jobs in the queue."""
    queue = get_job_queue()
    jobs = await queue.get_all()
    
    return [
        JobStatusResponse(
            job_id=j.job_id,
            status=j.status.value,
            progress=j.progress,
            created_at=j.created_at,
            started_at=j.started_at,
            completed_at=j.completed_at,
            result=j.result,
            error=j.error
        )
        for j in jobs
    ]


@router.post("/{job_id}/pause", response_model=ProcessResponse, responses={400: {"model": ErrorDetail}, 404: {"model": ErrorDetail}}, summary="Pause a processing job")
async def pause_job(job_id: str):
    """Pause a currently processing job."""
    queue = get_job_queue()
    job = await queue.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"})
    
    if job.status.value != "processing":
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": f"Cannot pause job with status: {job.status.value}"})
    
    success = await queue.pause(job_id)
    
    if success:
        return ProcessResponse(
            message=f"Job {job_id} paused successfully",
            job_id=job_id,
            total_files=0,
            links={"jobs": "/api/v1/process"}
        )
    else:
        raise HTTPException(status_code=400, detail={"code": "PAUSE_FAILED", "message": "Failed to pause job"})


@router.post("/{job_id}/resume", response_model=ProcessResponse, responses={400: {"model": ErrorDetail}, 404: {"model": ErrorDetail}}, summary="Resume a paused job")
async def resume_job(job_id: str):
    """Resume a paused job."""
    queue = get_job_queue()
    job = await queue.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"})
    
    if job.status.value != "paused":
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": f"Cannot resume job with status: {job.status.value}"})
    
    success = await queue.resume(job_id)
    
    if success:
        return ProcessResponse(
            message=f"Job {job_id} resumed successfully",
            job_id=job_id,
            total_files=0,
            links={"jobs": "/api/v1/process"}
        )
    else:
        raise HTTPException(status_code=400, detail={"code": "RESUME_FAILED", "message": "Failed to resume job"})


@router.post("/{job_id}/cancel", response_model=ProcessResponse, responses={400: {"model": ErrorDetail}, 404: {"model": ErrorDetail}}, summary="Cancel a job")
async def cancel_job(job_id: str):
    """Cancel a pending, processing, or paused job."""
    from ..services.job_queue import JobStatus
    
    queue = get_job_queue()
    job = await queue.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"})
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.PAUSED]:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": f"Cannot cancel job with status: {job.status.value}"})
    
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now().isoformat()
    await queue.update(job)
    
    return ProcessResponse(
        message=f"Job {job_id} cancelled successfully",
        job_id=job_id,
        total_files=0,
        links={"jobs": "/api/v1/process"}
    )


__all__ = ["router"]

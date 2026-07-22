"""
Background worker for processing jobs from the queue.
"""
import asyncio
import csv
import os
from datetime import datetime
from typing import List, Optional

from ..config import get_logger, set_worker_id
from ..core.state import processing_state, COLOR_PRESETS, get_job_state, cleanup_job_state
from ..core.utils import now_ts, append_log
from .job_queue import JobQueue, JobStatus, get_job_queue, create_job
from .pdf_highlighter import PDFHighlighter
from .docx_highlighter import DOCXHighlighter
from ..config.settings import get_settings

logger = get_logger(__name__)

OUTPUT_FOLDER = "output"


def _save_combined_log(logs: List[dict], base_folder: str, columns: str, job_id: str) -> str:
    """Save combined log to CSV file."""
    combined_path = os.path.join(
        base_folder,
        f"{job_id}_Matches.csv"
    )
    keys = ["File", "Page/Paragraph", "Columns", "Matched Value", "Matched Pair", "Timestamp", "Output File", "Note"]
    
    with open(combined_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in logs:
            writer.writerow({k: row.get(k, "") for k in keys})
    
    logger.info(f"Saved combined log: {combined_path}")
    return combined_path


def _save_not_found_report(not_found_values: List, base_folder: str, columns: str, job_id: str) -> Optional[str]:
    """Save report of values that were not found in documents."""
    if not not_found_values:
        return None
    
    # Single mode (pairs not supported for now)
    report_path = os.path.join(
        base_folder,
        f"{job_id}_Missing_values.csv"
    )
    with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"Values Not Found - Column: {columns}"])
        for val in not_found_values:
            w.writerow([val])
    
    logger.info(f"Saved not found report: {report_path}")
    return report_path


class QueueWorker:
    """Worker that processes jobs from the queue."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.queue: Optional[JobQueue] = None
        self.pdf_service = PDFHighlighter()
        self.docx_service = DOCXHighlighter()
        self.running = False
        self.workers: List[asyncio.Task] = []
    
    async def _check_and_handle_pause(self, job_id: str, current_progress: float) -> bool:
        """Check if job was paused and update status. Returns True if paused, False otherwise."""
        state = await get_job_state(job_id)
        if state.paused:
            state.progress = current_progress
            processing_state.status = "Paused"
            processing_state.running = False
            logger.info(f"Job {job_id} detected as paused at {current_progress}%")
            return True
        return False
    
    async def _update_progress(self, job_id: str, progress: float):
        """Update job progress in job-specific state."""
        state = await get_job_state(job_id)
        if state.status == "Processing...":
            state.progress = progress
        # Also update global state for backward compatibility
        processing_state.progress = progress
    
    async def start(self):
        """Start the worker pool."""
        self.queue = get_job_queue()
        self.running = True
        
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
        
        logger.info(f"Started {self.max_workers} queue workers")
    
    async def stop(self):
        """Stop the worker pool."""
        self.running = False
        
        for task in self.workers:
            task.cancel()
        
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Queue workers stopped")
    
    async def _worker_loop(self, worker_id: int):
        """Worker loop that processes jobs."""
        worker_name = f"Worker-{worker_id}"
        set_worker_id(worker_name)
        logger.info(f"{worker_name} started (queue_id={id(self.queue)})")
        
        empty_polls = 0
        while self.running:
            try:
                job = await asyncio.wait_for(self.queue.dequeue(), timeout=1.0)
                
                if job:
                    empty_polls = 0
                    logger.info(f"{worker_name} got job {job.job_id}")
                    await self._process_job(job)
                    logger.info(f"{worker_name} finished job {job.job_id}")
                else:
                    empty_polls += 1
                    if empty_polls % 10 == 0:
                        logger.debug(f"{worker_name} polling... ({empty_polls} empty polls)")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{worker_name} error: {e}", exc_info=True)
        
        logger.info(f"{worker_name} stopped")
    
    async def _process_job(self, job):
        """Process a single job."""
        try:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now().isoformat()
            job.progress = 0.0
            await self.queue.update(job)
            
            data = job.data
            if not data:
                job.status = JobStatus.FAILED
                job.error = "No job data provided"
                await self.queue.update(job)
                return
            
            # Check if job was paused before starting
            current_job = await self.queue.get(job.job_id)
            if current_job and current_job.status == JobStatus.PAUSED:
                job.status = JobStatus.PAUSED
                await self.queue.update(job)
                logger.info(f"Job {job.job_id} was paused before processing started")
                return
            
            result = await self._execute_processing(data, job.job_id)
            
            # Check if job was paused during processing
            current_job = await self.queue.get(job.job_id)
            if current_job and current_job.status == JobStatus.PAUSED:
                job.status = JobStatus.PAUSED
                job.progress = current_job.progress
                await self.queue.update(job)
                logger.info(f"Job {job.job_id} was paused during processing at {job.progress}%")
                return
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.progress = 100.0
            job.result = result
            await self.queue.update(job)
            
            logger.info(f"Job {job.job_id} completed successfully")
            # Note: State is NOT cleaned up here - frontend needs to see completion status
            # State will be cleaned up when the job is fetched via /api/v1/process/{job_id} DELETE
            # or after a timeout period
        
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()
            await self.queue.update(job)
            logger.error(f"Job {job.job_id} failed: {e}")
            
            # Clean up job-specific state on failure
            await cleanup_job_state(job.job_id)
    
    async def _execute_processing(self, data: dict, job_id: str = None) -> dict:
        """Execute the actual document processing."""
        from ..core.state import COLOR_PRESETS
        
        files = data.get("files", [])
        columns = data.get("columns", "")
        color = data.get("color", "Yellow")
        dest_folder = data.get("dest_folder")
        values = data.get("values", [])
        
        # Get custom highlight settings from environment variables
        settings = get_settings()
        highlight_padding = settings.highlight.padding
        
        logger.info(f"Full row highlight with padding: {highlight_padding}")
        
        total_files = len(files)
        total_matches = 0
        all_logs = []
        
        color_rgb = COLOR_PRESETS.get(color, COLOR_PRESETS["Yellow"])["pdf_rgb"]
        
        # Determine if multi-column mode
        cols = [c.strip() for c in columns.split(',') if c.strip()]
        is_multi = len(cols) > 1
        
        # Set dest_folder in processing_state
        # Always use OUTPUT_FOLDER as the destination for processed files
        # Ignore any dest_folder passed from frontend to ensure consistent output location
        dest_folder = OUTPUT_FOLDER
        os.makedirs(dest_folder, exist_ok=True)
        
        # Get job-specific state
        state = await get_job_state(job_id)
        state.dest_folder = dest_folder
        state.job_id = job_id
        state.logs.clear()  # Clear logs for new job
        state.current_job_pdfs = []  # Clear previous job files
        state.combined_log = None
        state.not_found_report = None
        state.status = "Processing..."
        state.running = True
        state.completed = False
        
        # Also update global state for backward compatibility
        processing_state.dest_folder = dest_folder
        processing_state.job_id = job_id
        processing_state.logs.clear()
        processing_state.current_job_pdfs = []
        processing_state.combined_log = None
        processing_state.not_found_report = None
        processing_state.status = "Processing..."
        processing_state.running = True
        processing_state.completed = False
        
        for idx, file_info in enumerate(files):
            # Check for pause before processing each file
            file_progress = (idx / len(files)) * 100
            if await self._check_and_handle_pause(job_id, file_progress):
                return {
                    "total_files": total_files,
                    "total_matches": total_matches,
                    "not_found_count": 0,
                    "not_found_report": None,
                    "combined_log": None,
                    "completed_at": now_ts(),
                    "dest_folder": dest_folder,
                    "paused": True,
                    "paused_at_progress": file_progress
                }
            
            filepath = file_info.get("path")
            logger.info(f"Processing file {idx+1}/{len(files)}: {filepath}")
            
            if not filepath:
                logger.warning(f"File {idx+1}: No filepath provided, skipping")
                continue
            
            # Check both relative and absolute paths
            if not os.path.isabs(filepath):
                # Try relative path first, then absolute in current directory
                if not os.path.exists(filepath):
                    abs_path = os.path.join(os.getcwd(), filepath)
                    if os.path.exists(abs_path):
                        filepath = abs_path
                        logger.info(f"Found file at absolute path: {filepath}")
                    else:
                        logger.error(f"File {idx+1}: File does not exist at: {filepath} (or {abs_path})")
                        continue
            elif not os.path.exists(filepath):
                logger.error(f"File {idx+1}: File does not exist at absolute path: {filepath}")
                continue
            
            logger.info(f"File {idx+1}: File exists, size: {os.path.getsize(filepath)} bytes")
            
            original_name = os.path.basename(filepath).replace("temp_doc_", "")
            
            matches, logs, output_path = 0, [], None
            
            if filepath.endswith(".pdf"):
                # Use PDFHighlighter service for both single and multi-column
                # The service uses pdf_highlighter_decider to route to appropriate engine
                matches, logs, output_path = self.pdf_service.highlight(
                    path=filepath,
                    data=values,
                    column_names=columns,
                    color_rgb=color_rgb,
                    original_filename=original_name,
                    idx=idx + 1,
                    job_id=job_id,
                    highlight_padding=highlight_padding
                )
            elif filepath.endswith(".docx"):
                matches, logs, output_path = self.docx_service.highlight(
                    path=filepath,
                    data=values,
                    column_names=columns,
                    color=color,
                    original_filename=original_name,
                    idx=idx + 1,
                    job_id=job_id
                )
            
            total_matches += matches
            all_logs.extend(logs)
            # Also add logs to processing_state for frontend polling
            for log_entry in logs:
                append_log(log_entry, state)  # Use job-specific state
            
            # Update progress after each file
            await self._update_progress(job_id, file_progress)
        
        # Final progress update to 100%
        state.progress = 100.0
        state.running = False
        await self._update_progress(job_id, 100.0)
        
        # Cleanup temp files after processing
        for file_info in files:
            filepath = file_info.get("path")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Cleaned up temp file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {filepath}: {e}")
        
        # Calculate not found values
        matched_values = set(log.get("Matched Value", "") for log in all_logs)
        not_found = [v for v in values if v not in matched_values]
        
        # Save CSV reports
        combined_log_path = _save_combined_log(all_logs, dest_folder, columns, job_id)
        not_found_report_path = _save_not_found_report(not_found, dest_folder, columns, job_id)
        
        # Store current job's output files in processing_state
        # Collect all highlighted PDFs for this job (deduplicated)
        job_output_files = []
        for f in os.listdir(dest_folder):
            # Match files that contain job_id and end with _Highlighted.pdf
            if job_id and job_id in f and f.endswith('_Highlighted.pdf'):
                job_output_files.append(f)
        
        # Store in job-specific state
        state.current_job_pdfs = job_output_files
        state.combined_log = os.path.basename(combined_log_path) if combined_log_path else None
        state.not_found_report = os.path.basename(not_found_report_path) if not_found_report_path else None
        
        # Update processing_state with completion info
        state.completed = True
        state.status = "Processing completed"
        
        return {
            "total_files": total_files,
            "total_matches": total_matches,
            "not_found_count": len(not_found),
            "not_found_report": not_found_report_path,
            "combined_log": combined_log_path,
            "completed_at": now_ts(),
            "dest_folder": dest_folder
        }


# Global worker instance
_worker: Optional[QueueWorker] = None


def get_queue_worker() -> QueueWorker:
    """Get the global queue worker instance."""
    global _worker
    if _worker is None:
        from ..config.settings import get_settings
        settings = get_settings()
        _worker = QueueWorker(max_workers=settings.workers or 4)
    return _worker


async def start_queue_workers():
    """Start all queue workers."""
    worker = get_queue_worker()
    await worker.start()
    return worker


async def stop_queue_workers():
    """Stop all queue workers."""
    global _worker
    if _worker:
        await _worker.stop()
        _worker = None

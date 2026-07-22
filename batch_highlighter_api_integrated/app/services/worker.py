"""
Background worker for processing files.
"""
import os
import csv
import asyncio
import time
from datetime import datetime
from typing import List, Union, Tuple, Optional

from ..config import get_logger, set_worker_id
from ..config.settings import get_settings
from ..core.state import processing_state, COLOR_PRESETS, update_state_safe
from ..core.utils import now_ts, append_log
from ..repositories.job_repository import JobRepository, get_job_repository
from .pdf_highlighter import PDFHighlighter
from .docx_highlighter import DOCXHighlighter


logger = get_logger(__name__)


class ProcessingWorker:
    """
    Worker class for processing files in background.
    
    Handles PDF and DOCX file highlighting with progress tracking.
    """
    
    def __init__(self, worker_id: str = "Worker-Main"):
        """Initialize the processing worker."""
        self.worker_id = worker_id
        set_worker_id(worker_id)
        self.pdf_service = PDFHighlighter()
        self.docx_service = DOCXHighlighter()
        self.job_repo: Optional[JobRepository] = None
        logger.info(f"{self.worker_id} initialized")
    
    async def initialize(self):
        """Initialize worker with job repository."""
        self.job_repo = get_job_repository()
    
    async def process_files(
        self,
        data: List[Union[str, Tuple[str, str]]],
        doc_files: List[str],
        dest_folder: Optional[str],
        selected_columns: str,
        selected_color: str,
        job_id: Optional[str] = None
    ) -> dict:
        """
        Process files with the given data.
        
        Args:
            data: Values or pairs to match
            doc_files: List of file paths to process
            dest_folder: Destination folder for output
            selected_columns: Column names
            selected_color: Highlight color
            
        Returns:
            Processing result dictionary
        """
        # Initialize state
        processing_state["logs"].clear()
        processing_state["running"] = True
        processing_state["paused"] = False
        processing_state["progress"] = 0.0
        processing_state["status"] = "Starting..."
        processing_state["selected_color"] = selected_color
        processing_state["start_time"] = now_ts()
        processing_state["end_time"] = None
        
        # Create job in repository
        actual_job_id = job_id
        if self.job_repo:
            total_values = len(data) if isinstance(data[0], str) else len(data)
            job = await self.job_repo.create_job(
                total_files=len(doc_files),
                total_values=total_values
            )
            actual_job_id = job.job_id
            processing_state["job_id"] = actual_job_id
            # Update worker ID to include job
            self.worker_id = f"Worker-{actual_job_id[:8]}"
            set_worker_id(self.worker_id)
            logger.info(f"{self.worker_id}: Created job: {actual_job_id}")
        
        # Setup output directory
        settings = get_settings()
        base_folder = os.path.join(
            settings.storage.base_output_dir,
            dest_folder or ""
        )
        os.makedirs(base_folder, exist_ok=True)
        processing_state["dest_folder"] = base_folder
        
        total_files = len(doc_files)
        all_logs = []
        total_matches_found = 0
        files_processed = 0
        
        try:
            for idx, fpath in enumerate(doc_files, start=1):
                if not processing_state["running"]:
                    logger.info("Processing stopped by user")
                    break
                
                # Update status with live progress
                current_file = os.path.basename(fpath)
                status_msg = f"Processing file {idx} of {total_files}: {current_file}"
                processing_state["status"] = status_msg
                processing_state["current_file"] = current_file
                processing_state["files_processed"] = idx - 1
                processing_state["progress"] = (idx - 1) / total_files * 100
                
                logger.info(status_msg)
                
                # Process file based on extension
                ext = os.path.splitext(fpath)[1].lower()
                original_name = os.path.basename(fpath).replace("temp_doc_", "")
                color_rgb = COLOR_PRESETS.get(selected_color, COLOR_PRESETS["Yellow"])["pdf_rgb"]
                
                matches_found_in_file = 0
                logs_local = []
                output_path = None
                
                logger.info(f"Starting to process: {original_name}")
                
                if ext == ".pdf":
                    matches_found_in_file, logs_local, output_path = self.pdf_service.highlight(
                        path=fpath,
                        data=data,
                        column_names=selected_columns,
                        color_rgb=color_rgb,
                        original_filename=original_name,
                        idx=idx,
                        job_id=job_id
                    )
                elif ext == ".docx":
                    matches_found_in_file, logs_local, output_path = self.docx_service.highlight(
                        path=fpath,
                        data=data,
                        column_names=selected_columns,
                        color=selected_color,
                        original_filename=original_name,
                        idx=idx,
                        job_id=job_id
                    )
                else:
                    logs_local = [{
                        "File": original_name,
                        "Page/Paragraph": "",
                        "Columns": selected_columns,
                        "Matched Value": "",
                        "Matched Pair": "",
                        "Timestamp": now_ts(),
                        "Output File": "",
                        "Note": "Unsupported file format - skipped",
                        "Error_Code": "UNSUPPORTED_FORMAT"
                    }]
                
                # Add logs to state and repository
                for r in logs_local:
                    append_log(r, processing_state)
                    all_logs.append(r)
                    
                    if self.job_repo and processing_state.get("job_id"):
                        await self.job_repo.add_log(processing_state["job_id"], r)
                
                # Update live progress
                files_processed = idx
                total_matches_found += matches_found_in_file
                processing_state["files_processed"] = files_processed
                processing_state["total_matches_found"] = total_matches_found
                processing_state["progress"] = idx / total_files * 100
                
                # Log real-time progress
                logger.info(
                    f"Progress: {files_processed}/{total_files} files processed, "
                    f"{total_matches_found} values highlighted so far"
                )
                
                # Update job repository
                if self.job_repo and processing_state.get("job_id"):
                    await self.job_repo.increment_progress(
                        processing_state["job_id"],
                        matched_count=matches_found_in_file
                    )
                
                # Check for pause
                while processing_state["paused"] and processing_state["running"]:
                    await asyncio.sleep(0.2)
            
            # Save combined log
            combined_path = self._save_combined_log(all_logs, base_folder)
            
            # Calculate values not found in documents
            not_found_values = self._calculate_not_found_values(data, all_logs, selected_columns)
            
            # Save not found values report
            not_found_report_path = self._save_not_found_report(not_found_values, base_folder, selected_columns)
            
            # Calculate completion summary
            total_values_to_process = len(data)
            completion_summary = {
                "total_files_to_process": len(doc_files),
                "files_successfully_processed": files_processed,
                "total_values_to_highlight": total_values_to_process,
                "values_found_and_highlighted": total_matches_found,
                "values_not_found": len(not_found_values),
                "completion_percentage": round((files_processed / len(doc_files)) * 100, 2) if doc_files else 100.0
            }
            
            # Complete the job
            processing_state.update({
                "running": False,
                "completed": True,
                "progress": 100.0,
                "status": "Processing completed successfully",
                "completion_summary": completion_summary,
                "combined_log": combined_path,
                "not_found_values_report": not_found_report_path,
                "end_time": now_ts()
            })
            
            # Update job repository
            if self.job_repo and processing_state.get("job_id"):
                await self.job_repo.complete_job(
                    processing_state["job_id"],
                    status="completed"
                )
            
            logger.info(
                f"Processing completed successfully. "
                f"Files: {files_processed}/{len(doc_files)}, "
                f"Values highlighted: {total_matches_found}, "
                f"Values not found: {len(not_found_values)}"
            )
            
            # Add helpful message if zero matches
            if total_matches_found == 0:
                logger.warning(
                    "No matches found. This usually means:\n"
                    "  1. The PDF doesn't contain the specified column(s)\n"
                    "  2. For multi-column mode, ALL columns must exist in the PDF\n"
                    "  3. Try single-column mode with a column that exists in the PDF\n"
                    "  4. Check the not_found_values_report CSV for which data wasn't found"
                )
            
            return {
                "success": True,
                "completion_summary": completion_summary,
                "combined_log": combined_path,
                "not_found_values_report": not_found_report_path
            }
            
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            
            # Mark job as failed
            if self.job_repo and processing_state.get("job_id"):
                await self.job_repo.complete_job(
                    processing_state["job_id"],
                    status="failed",
                    error=str(e)
                )
            
            raise
    
    def _save_combined_log(self, logs: List[dict], base_folder: str) -> str:
        """Save combined log to CSV file."""
        combined_path = os.path.join(
            base_folder,
            f"Matched_values_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        keys = ["File", "Page/Paragraph", "Columns", "Matched Pair", "Timestamp", "Output File", "Note"]
        
        with open(combined_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in logs:
                writer.writerow({k: row.get(k, "") for k in keys})
        
        return combined_path
    
    def _calculate_missing_values(
        self,
        data: List[Union[str, Tuple[str, str]]],
        logs: List[dict],
        columns: str
    ) -> List:
        """Calculate values that were not found in documents."""
        if isinstance(data[0], tuple) if data else False:
            # Pairs mode (multi-column matching)
            matched_pairs = set()
            for log in logs:
                pair = log.get("Matched Pair", "")
                if pair:
                    matched_pairs.add(tuple(pair.split(',')))
            return [p for p in data if p not in matched_pairs]
        else:
            # Single column mode
            matched_values = set(log.get("Matched Value", "") for log in logs)
            return [v for v in data if v not in matched_values]
    
    def _save_missing_report(
        self,
        missing_values: List,
        base_folder: str,
        columns: str
    ) -> Optional[str]:
        """Save report of values that were not found in documents."""
        if not missing_values:
            return None
        
        if isinstance(missing_values[0], tuple) if missing_values else False:
            # Pairs mode
            report_path = os.path.join(
                base_folder,
                f"Missing_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([f"Values Not Found - Columns: {columns}"])
                w.writerow([columns.split(',')[0] if ',' in columns else columns, 
                          columns.split(',')[1] if ',' in columns else ""])
                for p1, p2 in missing_values:
                    w.writerow([p1, p2])
        else:
            # Single mode
            report_path = os.path.join(
                base_folder,
                f"Missing_values_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([f"Values Not Found - Column: {columns}"])
                for val in missing_values:
                    w.writerow([val])
        
        return report_path
    
    # Backward compatibility aliases
    def _calculate_unmatched(self, data: List, logs: List[dict], columns: str) -> List:
        """Calculate unmatched values (backward compatibility alias)."""
        return self._calculate_missing_values(data, logs, columns)
    
    def _save_unmatched(self, unmatched: List, base_folder: str, columns: str) -> Optional[str]:
        """Save unmatched values (backward compatibility alias)."""
        return self._save_missing_report(unmatched, base_folder, columns)
    
    def _calculate_not_found_values(self, data: List, logs: List[dict], columns: str) -> List:
        """Calculate values not found (alias for _calculate_missing_values)."""
        return self._calculate_missing_values(data, logs, columns)
    
    def _save_not_found_report(self, not_found_values: List, base_folder: str, columns: str) -> Optional[str]:
        """Save not found report (alias for _save_missing_report)."""
        return self._save_missing_report(not_found_values, base_folder, columns)
    
    async def cleanup_temp_files(self, doc_files: List[str]):
        """Clean up temporary files."""
        try:
            for f in doc_files:
                if os.path.exists(f):
                    os.remove(f)
                    logger.debug(f"Cleaned up temp file: {f}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")


# Legacy function for backward compatibility
def worker_process(
    data: List[Union[str, Tuple[str, str]]],
    doc_files: List[str],
    dest_folder: Optional[str],
    selected_columns: str,
    selected_color: str
):
    """
    Legacy function for backward compatibility.
    Use ProcessingWorker class for new code.
    """
    worker = ProcessingWorker()
    asyncio.run(worker.process_files(
        data=data,
        doc_files=doc_files,
        dest_folder=dest_folder,
        selected_columns=selected_columns,
        selected_color=selected_color
    ))

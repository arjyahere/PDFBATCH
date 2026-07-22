"""
Job repository for tracking processing jobs.
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import uuid

from app.config.settings import get_settings


@dataclass
class Job:
    """Job model for tracking processing jobs."""
    job_id: str
    status: str  # pending, running, paused, completed, failed
    progress: float = 0.0
    total_files: int = 0
    processed_files: int = 0
    total_values: int = 0
    matched_values: int = 0
    unmatched_values: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create from dictionary."""
        return cls(**data)


class JobRepository:
    """
    Repository for managing processing jobs.
    
    Supports both in-memory storage (default) and file-based storage.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize job repository.
        
        Args:
            storage_path: Path to store job data (optional, for persistence)
        """
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._storage_path = storage_path
        self._load_from_disk()
    
    async def create_job(
        self,
        total_files: int,
        total_values: int = 0
    ) -> Job:
        """
        Create a new job.
        
        Args:
            total_files: Number of files to process
            total_values: Number of values to match
            
        Returns:
            Created Job instance
        """
        async with self._lock:
            job_id = str(uuid.uuid4())
            job = Job(
                job_id=job_id,
                status="pending",
                total_files=total_files,
                total_values=total_values
            )
            self._jobs[job_id] = job
            await self._save_to_disk(job)
            return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job instance or None if not found
        """
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update_job(
        self,
        job_id: str,
        **kwargs
    ) -> Optional[Job]:
        """
        Update job attributes.
        
        Args:
            job_id: Job identifier
            **kwargs: Attributes to update
            
        Returns:
            Updated Job instance or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                job.updated_at = datetime.now().isoformat()
                await self._save_to_disk(job)
            return job
    
    async def add_log(self, job_id: str, log_entry: Dict[str, Any]) -> Optional[Job]:
        """
        Add log entry to job.
        
        Args:
            job_id: Job identifier
            log_entry: Log entry to add
            
        Returns:
            Updated Job instance or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.logs.append(log_entry)
                job.updated_at = datetime.now().isoformat()
                await self._save_to_disk(job)
            return job
    
    async def increment_progress(
        self,
        job_id: str,
        matched_count: int = 0
    ) -> Optional[Job]:
        """
        Increment job progress.
        
        Args:
            job_id: Job identifier
            matched_count: Number of matches in this file
            
        Returns:
            Updated Job instance or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.processed_files += 1
                job.matched_values += matched_count
                job.progress = (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0
                job.updated_at = datetime.now().isoformat()
                await self._save_to_disk(job)
            return job
    
    async def complete_job(
        self,
        job_id: str,
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[Job]:
        """
        Mark job as completed.
        
        Args:
            job_id: Job identifier
            status: Final status (completed, failed)
            error: Error message if failed
            
        Returns:
            Updated Job instance or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.progress = 100.0
                job.completed_at = datetime.now().isoformat()
                job.error = error
                job.updated_at = datetime.now().isoformat()
                await self._save_to_disk(job)
            return job
    
    async def list_jobs(self, limit: int = 50) -> List[Job]:
        """
        List all jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs (most recent first)
        """
        async with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                await self._delete_from_disk(job_id)
                return True
            return False
    
    async def _save_to_disk(self, job: Job):
        """Save job to disk if storage path is configured."""
        if self._storage_path:
            Path(self._storage_path).mkdir(parents=True, exist_ok=True)
            job_path = Path(self._storage_path) / f"{job.job_id}.json"
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job.to_dict(), f, indent=2)
    
    async def _delete_from_disk(self, job_id: str):
        """Delete job file from disk."""
        if self._storage_path:
            job_path = Path(self._storage_path) / f"{job_id}.json"
            if job_path.exists():
                job_path.unlink()
    
    def _load_from_disk(self):
        """Load jobs from disk."""
        if self._storage_path:
            Path(self._storage_path).mkdir(parents=True, exist_ok=True)
            for job_path in Path(self._storage_path).glob("*.json"):
                try:
                    with open(job_path, encoding="utf-8") as f:
                        job_data = json.load(f)
                        job = Job.from_dict(job_data)
                        self._jobs[job.job_id] = job
                except Exception:
                    # Skip corrupted job files
                    pass


# Global job repository instance
_job_repository: Optional[JobRepository] = None


def get_job_repository() -> JobRepository:
    """
    Get job repository instance.
    
    Returns:
        JobRepository instance
    """
    global _job_repository
    if _job_repository is None:
        settings = get_settings()
        storage_path = None
        if settings.database.enabled and settings.database.type == "sqlite":
            storage_path = settings.database.sqlite_path
        _job_repository = JobRepository(storage_path=storage_path)
    return _job_repository

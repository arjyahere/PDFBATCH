"""
Job queue service for concurrent processing.
Supports both Redis (production) and in-memory (development) queues.
"""
import asyncio
import json
import uuid
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from ..config import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class Job:
    job_id: str
    user_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        if isinstance(data.get("status"), str):
            data["status"] = JobStatus(data["status"])
        return cls(**data)


class JobQueue(ABC):
    """Base job queue interface for managing async job processing.
    
    This abstract class defines the interface for job queue implementations.
    Subclasses must implement all methods for specific queue backends.
    """
    
    @abstractmethod
    async def enqueue(self, job: "Job") -> bool:
        """Add a job to the queue.
        
        Args:
            job: The job to add to the queue.
            
        Returns:
            True if the job was successfully enqueued, False otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def dequeue(self) -> Optional["Job"]:
        """Remove and return the next job from the queue.
        
        Returns:
            The next job in the queue, or None if empty.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get(self, job_id: str) -> Optional["Job"]:
        """Retrieve a job by its ID.
        
        Args:
            job_id: The unique identifier of the job.
            
        Returns:
            The job if found, None otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def update(self, job: "Job") -> bool:
        """Update an existing job.
        
        Args:
            job: The job with updated data.
            
        Returns:
            True if the job was successfully updated, False otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_all(self) -> List["Job"]:
        """Retrieve all jobs in the queue.
        
        Returns:
            List of all jobs.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def clear(self) -> bool:
        """Remove all jobs from the queue.
        
        Returns:
            True if the queue was successfully cleared, False otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def pause(self, job_id: str) -> bool:
        """Pause a job by ID.
        
        Args:
            job_id: The unique identifier of the job to pause.
            
        Returns:
            True if the job was successfully paused, False otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def resume(self, job_id: str) -> bool:
        """Resume a paused job by ID.
        
        Args:
            job_id: The unique identifier of the job to resume.
            
        Returns:
            True if the job was successfully resumed, False otherwise.
        """
        raise NotImplementedError


class FairJobQueue(JobQueue):
    """Fair in-memory job queue that ensures equal distribution of jobs to workers.
    
    This queue uses a dedicated Condition variable to ensure all waiting workers
    are notified when a job is added, providing fair FIFO distribution.
    """
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._cond = asyncio.Condition(self._lock)
        logger.info("Initialized fair in-memory job queue (id=%d)", id(self))
    
    async def enqueue(self, job: Job) -> bool:
        async with self._lock:
            self._jobs[job.job_id] = job
            await self._queue.put(job.job_id)
            queue_size = self._queue.qsize()
            # Notify ALL waiting workers that a job is available
            self._cond.notify_all()
            logger.info(f"Job {job.job_id} enqueued (queue_size={queue_size})")
            return True
    
    async def dequeue(self) -> Optional[Job]:
        async with self._cond:
            # Wait for a job to be available
            while True:
                try:
                    # Try to get from queue with timeout
                    job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    job = self._jobs.get(job_id)
                    if job:
                        job.status = JobStatus.PROCESSING
                        job.started_at = datetime.now().isoformat()
                        logger.debug(f"Worker got job {job_id}")
                    else:
                        logger.warning(f"Job {job_id} not found in jobs dict")
                    return job
                except asyncio.TimeoutError:
                    # Check if we should continue waiting
                    if self._queue.empty():
                        # No jobs, wait for notification
                        try:
                            await asyncio.wait_for(self._cond.wait(), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass
                        # Loop back and try again
    
    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update(self, job: Job) -> bool:
        async with self._lock:
            if job.job_id in self._jobs:
                self._jobs[job.job_id] = job
                return True
            return False
    
    async def get_all(self) -> list:
        async with self._lock:
            return list(self._jobs.values())
    
    async def clear(self) -> bool:
        async with self._lock:
            self._jobs.clear()
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._cond.notify_all()  # Wake up any waiting workers
            logger.info("Job queue cleared")
            return True
    
    async def pause(self, job_id: str) -> bool:
        """Pause a job by ID."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PROCESSING:
                job.status = JobStatus.PAUSED
                logger.info(f"Job {job_id} paused")
                return True
            return False
    
    async def resume(self, job_id: str) -> bool:
        """Resume a paused job by ID."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PAUSED:
                job.status = JobStatus.PENDING
                await self._queue.put(job_id)
                self._cond.notify_all()  # Notify workers that a resumed job is available
                logger.info(f"Job {job_id} resumed and requeued")
                return True
            return False


class InMemoryJobQueue(JobQueue):
    """In-memory job queue for development and single-instance deployments.
    
    NOTE: This implementation may have issues with fair job distribution
    when using asyncio.Queue with multiple workers. Use FairJobQueue instead
    for better worker distribution.
    """
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        logger.info("Initialized in-memory job queue (id=%d) - Consider using FairJobQueue for better distribution", id(self))
    
    async def enqueue(self, job: Job) -> bool:
        async with self._lock:
            self._jobs[job.job_id] = job
            await self._queue.put(job.job_id)
            queue_size = self._queue.qsize()
            logger.info(f"Job {job.job_id} enqueued (queue_size={queue_size})")
            return True
    
    async def dequeue(self) -> Optional[Job]:
        try:
            job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            async with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.PROCESSING
                    job.started_at = datetime.now().isoformat()
                    logger.debug(f"Dequeued job {job_id}")
                else:
                    logger.warning(f"Job {job_id} found in queue but not in _jobs dict")
                return job
        except asyncio.TimeoutError:
            return None
    
    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update(self, job: Job) -> bool:
        async with self._lock:
            if job.job_id in self._jobs:
                self._jobs[job.job_id] = job
                return True
            return False
    
    async def get_all(self) -> list:
        async with self._lock:
            return list(self._jobs.values())
    
    async def clear(self) -> bool:
        async with self._lock:
            self._jobs.clear()
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.info("Job queue cleared")
            return True
    
    async def pause(self, job_id: str) -> bool:
        """Pause a job by ID."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PROCESSING:
                job.status = JobStatus.PAUSED
                logger.info(f"Job {job_id} paused")
                return True
            return False
    
    async def resume(self, job_id: str) -> bool:
        """Resume a paused job by ID."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PAUSED:
                job.status = JobStatus.PENDING
                await self._queue.put(job_id)
                logger.info(f"Job {job_id} resumed and requeued")
                return True
            return False


class RedisJobQueue(JobQueue):
    """Redis-based job queue for production multi-instance deployments."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._redis = None
        self._queue_key = "batch_highlighter:jobs"
        self._jobs_key = "batch_highlighter:jobs:data"
    
    async def connect(self):
        """Connect to Redis using async client."""
        try:
            from redis.asyncio import Redis
            self._redis = Redis.from_url(self._redis_url)
            await self._redis.ping()
            logger.info(f"Connected to Redis at {self._redis_url}")
        except ImportError:
            logger.error("Redis package not installed. Install it with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def enqueue(self, job: Job) -> bool:
        if not self._redis:
            await self.connect()
        
        job_data = json.dumps(job.to_dict())
        await self._redis.hset(self._jobs_key, job.job_id, job_data)
        await self._redis.rpush(self._queue_key, job.job_id)
        logger.info(f"Job {job.job_id} enqueued to Redis")
        return True
    
    async def dequeue(self) -> Optional[Job]:
        if not self._redis:
            await self.connect()
        
        job_id = await self._redis.blpop(self._queue_key, timeout=1)
        if job_id:
            job_id = job_id[1].decode() if isinstance(job_id[1], bytes) else job_id[1]
            job_data = await self._redis.hget(self._jobs_key, job_id)
            if job_data:
                job = Job.from_dict(json.loads(job_data))
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now().isoformat()
                await self.update(job)
                return job
        return None
    
    async def get(self, job_id: str) -> Optional[Job]:
        if not self._redis:
            await self.connect()
        
        job_data = await self._redis.hget(self._jobs_key, job_id)
        if job_data:
            return Job.from_dict(json.loads(job_data))
        return None
    
    async def update(self, job: Job) -> bool:
        if not self._redis:
            await self.connect()
        
        job_data = json.dumps(job.to_dict())
        await self._redis.hset(self._jobs_key, job.job_id, job_data)
        return True
    
    async def get_all(self) -> list:
        if not self._redis:
            await self.connect()
        
        all_jobs = await self._redis.hgetall(self._jobs_key)
        jobs = []
        for job_data in all_jobs.values():
            jobs.append(Job.from_dict(json.loads(job_data)))
        return jobs
    
    async def clear(self) -> bool:
        if not self._redis:
            await self.connect()
        
        await self._redis.delete(self._queue_key, self._jobs_key)
        logger.info("Redis job queue cleared")
        return True
    
    async def pause(self, job_id: str) -> bool:
        """Pause a job by ID."""
        if not self._redis:
            await self.connect()
        
        job_data = await self._redis.hget(self._jobs_key, job_id)
        if job_data:
            job = Job.from_dict(json.loads(job_data))
            if job.status == JobStatus.PROCESSING:
                job.status = JobStatus.PAUSED
                await self.update(job)
                logger.info(f"Job {job_id} paused")
                return True
        return False
    
    async def resume(self, job_id: str) -> bool:
        """Resume a paused job by ID."""
        if not self._redis:
            await self.connect()
        
        job_data = await self._redis.hget(self._jobs_key, job_id)
        if job_data:
            job = Job.from_dict(json.loads(job_data))
            if job.status == JobStatus.PAUSED:
                job.status = JobStatus.PENDING
                await self.update(job)
                await self._redis.rpush(self._queue_key, job_id)
                logger.info(f"Job {job_id} resumed and requeued")
                return True
        return False


# Global job queue instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        from ..config.settings import get_settings
        settings = get_settings()
        
        if settings.database.enabled and settings.database.type == "redis":
            _job_queue = RedisJobQueue(settings.database.redis_url)
            logger.info("Using Redis job queue")
        else:
            # Use FairJobQueue for better worker distribution
            _job_queue = FairJobQueue()
            logger.info("Using FairJobQueue for better worker distribution")
    
    return _job_queue


def create_job(data: Dict[str, Any], job_id: Optional[str] = None, user_id: Optional[str] = None) -> Job:
    """Create a new job."""
    if job_id is None:
        job_id = str(uuid.uuid4())
    return Job(
        job_id=job_id,
        user_id=user_id,
        status=JobStatus.PENDING,
        data=data
    )

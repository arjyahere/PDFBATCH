"""
Application state management.
"""
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from app.config import get_logger


logger = get_logger(__name__)


@dataclass
class ProcessingState:
    """Structured processing state."""
    running: bool = False
    paused: bool = False
    progress: float = 0.0
    status: str = "Idle"
    logs: List[Dict[str, Any]] = field(default_factory=list)
    combined_log: Optional[str] = None
    not_found_report: Optional[str] = None
    dest_folder: str = ""
    selected_color: str = "Yellow"
    job_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    completed: bool = False
    current_file: Optional[str] = None
    files_processed: int = 0
    total_matches_found: int = 0
    completion_summary: Optional[Dict[str, Any]] = None
    # Current job specific output files
    current_job_pdfs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingState":
        return cls(**data)
    
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
    
    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)
    
    def __delitem__(self, key: str):
        delattr(self, key)
    
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)
    
    def keys(self):
        return self.__dataclass_fields__.keys()
    
    def values(self):
        return [getattr(self, k) for k in self.keys()]
    
    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]
    
    def update(self, data: Dict[str, Any]):
        for key, value in data.items():
            setattr(self, key, value)


# Legacy global state for backward compatibility
state_lock = asyncio.Lock()
processing_state = ProcessingState()

# Job-specific states for concurrent processing
_job_states: Dict[str, ProcessingState] = {}
_job_states_lock = asyncio.Lock()


async def get_job_state(job_id: str) -> ProcessingState:
    """Get or create a job-specific processing state."""
    async with _job_states_lock:
        if job_id not in _job_states:
            _job_states[job_id] = ProcessingState()
            _job_states[job_id].job_id = job_id
            logger.debug(f"Created job state for {job_id}")
        return _job_states[job_id]


async def cleanup_job_state(job_id: str):
    """Clean up job-specific state after job completion."""
    async with _job_states_lock:
        if job_id in _job_states:
            del _job_states[job_id]
            logger.debug(f"Cleaned up job state for {job_id}")


async def update_state_safe(key: str, value: Any):
    """Thread-safe state update using asyncio.Lock."""
    async with state_lock:
        setattr(processing_state, key, value)
        logger.debug(f"State updated: {key} = {value}")


async def get_state_safe() -> Dict[str, Any]:
    """Thread-safe state read."""
    async with state_lock:
        return processing_state.to_dict()


async def reset_state(clear_logs: bool = True):
    """Reset processing state."""
    async with state_lock:
        processing_state.running = False
        processing_state.paused = False
        processing_state.progress = 0.0
        processing_state.status = "Idle"
        processing_state.completed = False
        if clear_logs:
            processing_state.logs.clear()
        processing_state.combined_log = None
        processing_state.not_found_report = None
        processing_state.dest_folder = ""
        processing_state.job_id = None
        processing_state.start_time = None
        processing_state.end_time = None
        processing_state.current_file = None
        processing_state.files_processed = 0
        processing_state.total_matches_found = 0
        processing_state.completion_summary = None
        processing_state.current_job_pdfs = []
        logger.info("Processing state reset")


# Color presets for highlighting
COLOR_PRESETS = {
    "Yellow": {"pdf_rgb": (1.0, 1.0, 0.2), "word_val": "yellow", "docx_enum": "yellow"},
    "Green":  {"pdf_rgb": (0.66, 1.0, 0.33), "word_val": "green", "docx_enum": "green"},
    "Cyan":   {"pdf_rgb": (0.4, 1.0, 1.0),  "word_val": "cyan", "docx_enum": "cyan"},
    "Pink":   {"pdf_rgb": (1.0, 0.6, 0.86), "word_val": "magenta", "docx_enum": "magenta"},
    "Blue":   {"pdf_rgb": (0.6, 0.85, 1.0), "word_val": "blue", "docx_enum": "blue"},
    "Red":    {"pdf_rgb": (1.0, 0.55, 0.55), "word_val": "red", "docx_enum": "red"},
}


logger.info("Initializing processing state")

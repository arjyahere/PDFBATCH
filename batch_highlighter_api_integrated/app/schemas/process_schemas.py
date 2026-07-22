from typing import List, Optional
from pydantic import BaseModel, Field

class ProcessRequest(BaseModel):
    selected_columns: str
    selected_color: str = "Yellow"
    destination_folder: Optional[str] = None

class ProcessResponse(BaseModel):
    message: str = "Processing started"
    job_id: str
    total_values: Optional[int] = None
    total_pairs: Optional[int] = None
    total_files: int
    progress_url: str = "/api/v1/progress"
    status_url: str = "/api/v1/status"
    links: dict = Field(default_factory=dict)

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float = Field(0, ge=0, le=100)
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

class ProcessResult(BaseModel):
    job_id: str
    status: str
    progress: float = Field(0, ge=0, le=100)
    total_files: int
    processed_files: int
    total_matches: int
    unmatched_values: Optional[List[str]] = None
    unmatched_pairs: Optional[List[tuple]] = None
    output_files: List[str] = Field(default_factory=list)
    logs: List["ProcessingLog"] = Field(default_factory=list)

class ProcessingStatus(BaseModel):
    running: bool
    paused: bool
    progress: float = Field(0, ge=0, le=100)
    status: str
    job_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    completed: bool = False
    current_file: Optional[str] = None
    files_processed: int = 0
    total_matches_found: int = 0
    completion_summary: Optional[dict] = None
    logs: list = Field(default_factory=list)
    combined_log: str = ""
    not_found_report: str = ""
    output_files: list = Field(default_factory=list)

class HighlightMatch(BaseModel):
    file: str
    page: Optional[str] = None
    paragraph: Optional[str] = None
    matched_value: Optional[str] = None
    matched_pair: Optional[str] = None
    output_file: Optional[str] = None
    note: Optional[str] = None
    timestamp: str

class ProcessingLog(BaseModel):
    file: str
    page_paragraph: Optional[str] = ""
    columns: str
    matched_value: Optional[str] = ""
    matched_pair: Optional[str] = ""
    timestamp: float
    output_file: Optional[str] = ""
    note: Optional[str] = ""
    error_code: Optional[str] = ""

ProcessResult.update_forward_refs()

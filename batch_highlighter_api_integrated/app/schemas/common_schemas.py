from typing import Optional
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    timestamp: str

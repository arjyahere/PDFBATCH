from datetime import datetime
from typing import Any

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_filename(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in (" ", "_", "-", "(", ")")).rstrip()

def append_log(entry: dict, processing_state: Any):
    """Append log entry to processing state. Works with both dict and dataclass."""
    if hasattr(processing_state, 'logs'):
        # Handle dataclass/object with logs attribute
        processing_state.logs.append(entry)
    elif isinstance(processing_state, dict):
        # Handle dict-like object
        processing_state["logs"].append(entry)

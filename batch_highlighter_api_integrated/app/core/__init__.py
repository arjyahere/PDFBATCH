"""
Core module for the application.

This module provides core functionality including:
- Configuration management
- State management
- Exception handling
- Utilities
"""
import warnings

# Suppress deprecation warnings for backward compatibility
warnings.filterwarnings("ignore", category=DeprecationWarning)

from app.config import setup_logging, get_logger
from .state import (
    processing_state,
    state_lock,
    COLOR_PRESETS,
    ProcessingState,
    update_state_safe,
    get_state_safe,
    reset_state,
    get_job_state,
    cleanup_job_state,
)
from .exceptions import (
    AppException,
    FileException,
    FileNotFoundException,
    FilePermissionException,
    InvalidFileFormatException,
    ProcessingException,
    ValidationException,
    ConfigurationException,
)
from .exception_handlers import setup_exception_handlers
from .utils import now_ts, safe_filename, append_log

# Backward compatibility - re-export error_codes functions
from . import error_codes

# Keep format_error available for backward compatibility
format_error = error_codes.format_error

__all__ = [
    # Config (from app.config)
    "setup_logging",
    "get_logger",
    # State
    "processing_state",
    "state_lock",
    "COLOR_PRESETS",
    "ProcessingState",
    "update_state_safe",
    "get_state_safe",
    "reset_state",
    "get_job_state",
    "cleanup_job_state",
    # Exceptions
    "AppException",
    "FileException",
    "FileNotFoundException",
    "FilePermissionException",
    "InvalidFileFormatException",
    "ProcessingException",
    "ValidationException",
    "ConfigurationException",
    # Exception handlers
    "setup_exception_handlers",
    # Utils
    "now_ts",
    "safe_filename",
    "append_log",
    # Backward compatibility
    "format_error",
    "error_codes",
]

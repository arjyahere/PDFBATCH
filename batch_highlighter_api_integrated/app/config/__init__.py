"""
Configuration module for the application.

Provides:
- Settings management with Pydantic
- Logging configuration
- Environment variable support
"""
from .settings import settings, get_settings
from .logging_config import setup_logging, get_logger, set_worker_id, get_worker_id

__all__ = ["settings", "get_settings", "setup_logging", "get_logger", "set_worker_id", "get_worker_id"]

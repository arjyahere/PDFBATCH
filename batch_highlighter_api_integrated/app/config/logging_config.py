"""
Logging configuration for the application.
"""
import os
import logging
import threading
from logging.handlers import RotatingFileHandler
from typing import Optional

from .settings import settings

# Thread-local storage for worker identification
_worker_context = threading.local()


def get_worker_id() -> str:
    """Get the current worker ID from thread-local storage."""
    return getattr(_worker_context, 'worker_id', 'main')


def set_worker_id(worker_id: str):
    """Set the current worker ID in thread-local storage."""
    _worker_context.worker_id = worker_id


class WorkerLogFormatter(logging.Formatter):
    """Custom formatter that includes worker ID in log output."""
    
    def format(self, record):
        # Add worker_id to the record
        record.worker_id = get_worker_id()
        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Setup application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        log_format: Log format string
        
    Returns:
        Configured logger instance
    """
    # Use settings or provided values
    level = log_level or settings.logging.level
    file_path = log_file or settings.logging.file_path
    fmt = log_format or settings.logging.format
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get logger
    logger = logging.getLogger("batch_highlighter")
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters with worker_id support
    console_formatter = WorkerLogFormatter(
        fmt.replace('%(message)s', '[%(worker_id)s] %(message)s')
    )
    file_formatter = WorkerLogFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - [%(worker_id)s] - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=settings.logging.max_bytes,
        backupCount=settings.logging.backup_count,
        encoding='utf-8-sig'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"batch_highlighter.{name}")

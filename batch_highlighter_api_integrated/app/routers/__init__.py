"""
API Routers module.
"""
from .process_router import router as process_router
from .progress_router import router as progress_router
from .download_router import router as download_router
from .misc_router import router as misc_router

__all__ = [
    "process_router",
    "progress_router",
    "download_router",
    "misc_router",
]

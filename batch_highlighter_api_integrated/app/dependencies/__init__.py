"""
Dependency injection module for the application.
"""
from .service_factory import (
    get_pdf_service,
    get_docx_service,
    get_highlight_service,
    get_file_service,
    ServiceFactory,
)

__all__ = [
    "get_pdf_service",
    "get_docx_service",
    "get_highlight_service",
    "get_file_service",
    "ServiceFactory",
]

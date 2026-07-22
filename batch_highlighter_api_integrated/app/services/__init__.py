"""
Services module for the application.
"""
from .pdf_highlighter import PDFHighlighter
from .docx_highlighter import DOCXHighlighter
from .worker import ProcessingWorker

__all__ = [
    "PDFHighlighter",
    "DOCXHighlighter",
    "ProcessingWorker",
]

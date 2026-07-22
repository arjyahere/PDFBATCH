"""
Service factory for dependency injection.
"""
from typing import Protocol, runtime_checkable
from app.services.pdf_highlighter import PDFHighlighter
from app.services.docx_highlighter import DOCXHighlighter


@runtime_checkable
class PDFServiceProtocol(Protocol):
    """Protocol for PDF highlighting service."""
    def highlight(self, path: str, data: list, column_names: str, color_rgb: tuple, original_filename: str, idx: int):
        ...


@runtime_checkable
class DOCXServiceProtocol(Protocol):
    """Protocol for DOCX highlighting service."""
    def highlight(self, path: str, data: list, column_names: str, color: str, original_filename: str, idx: int):
        ...


class ServiceFactory:
    """
    Factory for creating service instances.
    
    This factory provides dependency injection for services,
    making it easy to swap implementations or mock them for testing.
    """
    
    _pdf_service: PDFServiceProtocol = None
    _docx_service: DOCXServiceProtocol = None
    
    @classmethod
    def get_pdf_service(cls) -> PDFServiceProtocol:
        """
        Get PDF highlighting service.
        
        Returns:
            PDFHighlighter instance
        """
        if cls._pdf_service is None:
            cls._pdf_service = PDFHighlighter()
        return cls._pdf_service
    
    @classmethod
    def get_docx_service(cls) -> DOCXServiceProtocol:
        """
        Get DOCX highlighting service.
        
        Returns:
            DOCXHighlighter instance
        """
        if cls._docx_service is None:
            cls._docx_service = DOCXHighlighter()
        return cls._docx_service
    
    @classmethod
    def get_highlight_service(cls, file_extension: str) -> PDFServiceProtocol | DOCXServiceProtocol:
        """
        Get appropriate highlighting service by file extension.
        
        Args:
            file_extension: File extension (pdf, docx)
            
        Returns:
            Appropriate highlighting service
        """
        ext = file_extension.lower()
        if ext == ".pdf":
            return cls.get_pdf_service()
        elif ext == ".docx":
            return cls.get_docx_service()
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
    
    @classmethod
    def reset(cls):
        """Reset all service instances (useful for testing)."""
        cls._pdf_service = None
        cls._docx_service = None


# Convenience functions for FastAPI dependency injection
def get_pdf_service() -> PDFServiceProtocol:
    """Dependency for PDF service."""
    return ServiceFactory.get_pdf_service()


def get_docx_service() -> DOCXServiceProtocol:
    """Dependency for DOCX service."""
    return ServiceFactory.get_docx_service()


def get_highlight_service(extension: str) -> PDFServiceProtocol | DOCXServiceProtocol:
    """Dependency for highlight service based on extension."""
    return ServiceFactory.get_highlight_service(extension)

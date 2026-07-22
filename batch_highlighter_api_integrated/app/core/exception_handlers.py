"""
Exception handlers for the application.
"""
from typing import Union
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from app.config import get_logger
from app.core.exceptions import (
    AppException,
    FileException,
    ProcessingException,
    ValidationException,
    ConfigurationException,
)


logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.
    
    Args:
        request: FastAPI request
        exc: Application exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"App exception: code={exc.code}, detail={exc.detail}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        },
        headers=getattr(exc, "headers", None)
    )


async def file_exception_handler(request: Request, exc: FileException) -> JSONResponse:
    """
    Handle file-related exceptions.
    
    Args:
        request: FastAPI request
        exc: File exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"File exception: code={exc.code}, file={exc.file_path}, detail={exc.detail}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "file": exc.file_path,
                "path": str(request.url.path)
            }
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """
    Handle validation exceptions.
    
    Args:
        request: FastAPI request
        exc: Validation exception
        
    Returns:
        JSON response with error details
    """
    logger.warning(
        f"Validation error: code={exc.code}, field={exc.field}, detail={exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "field": exc.field,
                "path": str(request.url.path)
            }
        }
    )


async def processing_exception_handler(request: Request, exc: ProcessingException) -> JSONResponse:
    """
    Handle processing exceptions.
    
    Args:
        request: FastAPI request
        exc: Processing exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Processing error: code={exc.code}, job_id={exc.job_id}, detail={exc.detail}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "job_id": exc.job_id,
                "path": str(request.url.path)
            }
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Args:
        request: FastAPI request
        exc: Unexpected exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "path": str(request.url.path)
            }
        }
    )


def setup_exception_handlers(app: FastAPI):
    """
    Setup all exception handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(FileException, file_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ProcessingException, processing_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

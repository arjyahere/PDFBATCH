"""
Custom exceptions for the application.
"""
from typing import Optional, Any
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


class FileException(AppException):
    """Exception for file-related errors."""
    
    def __init__(
        self,
        detail: str,
        code: str = "FILE_ERROR",
        file_path: Optional[str] = None,
        **kwargs
    ):
        self.file_path = file_path
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
            **kwargs
        )


class FileNotFoundException(FileException):
    """Exception when file is not found."""
    
    def __init__(self, file_path: str):
        super().__init__(
            detail=f"File not found: {file_path}",
            code="FILE_NOT_FOUND",
            file_path=file_path
        )


class FilePermissionException(FileException):
    """Exception when file permission is denied."""
    
    def __init__(self, file_path: str):
        super().__init__(
            detail=f"Permission denied for file: {file_path}",
            code="FILE_PERMISSION_DENIED",
            file_path=file_path
        )


class InvalidFileFormatException(FileException):
    """Exception when file format is invalid."""
    
    def __init__(self, file_path: str, expected_format: str):
        super().__init__(
            detail=f"Invalid file format for {file_path}. Expected: {expected_format}",
            code="FILE_INVALID_FORMAT",
            file_path=file_path
        )


class ProcessingException(AppException):
    """Exception for processing errors."""
    
    def __init__(
        self,
        detail: str,
        code: str = "PROCESSING_ERROR",
        job_id: Optional[str] = None
    ):
        self.job_id = job_id
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code
        )


class ValidationException(AppException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        detail: str,
        code: str = "VALIDATION_ERROR",
        field: Optional[str] = None
    ):
        self.field = field
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code=code
        )


class ConfigurationException(AppException):
    """Exception for configuration errors."""
    
    def __init__(self, detail: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code="CONFIGURATION_ERROR"
        )

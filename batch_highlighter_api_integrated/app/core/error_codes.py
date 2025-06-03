import datetime
import socket
import uuid

# Error categories and codes
ERROR_CATEGORIES = {
    "FILE_ERROR": "File operation errors",
    "DATA_ERROR": "Data processing errors",
    "VALIDATION_ERROR": "Input validation errors",
    "PROCESSING_ERROR": "Document processing errors",
    "SYSTEM_ERROR": "System or unexpected errors",
    "NETWORK_ERROR": "Network-related errors",
    "AUTHENTICATION_ERROR": "Authentication and authorization errors",
    "CONFIGURATION_ERROR": "Configuration-related errors"
}

# Specific error codes
ERROR_CODES = {
    # File errors
    "FILE_NOT_FOUND": {"category": "FILE_ERROR", "title": "File Not Found", "description": "The specified file could not be located."},
    "FILE_PERMISSION_DENIED": {"category": "FILE_ERROR", "title": "Permission Denied", "description": "Access to the file is denied due to permissions."},
    "FILE_INVALID_FORMAT": {"category": "FILE_ERROR", "title": "Invalid File Format", "description": "The file format is not supported or invalid."},
    "FILE_TOO_LARGE": {"category": "FILE_ERROR", "title": "File Too Large", "description": "The file exceeds the maximum allowed size."},

    # Data errors
    "DATA_CORRUPTED": {"category": "DATA_ERROR", "title": "Data Corrupted", "description": "The data is corrupted and cannot be processed."},
    "DATA_MISSING": {"category": "DATA_ERROR", "title": "Data Missing", "description": "Required data is missing."},
    "DATA_INVALID": {"category": "DATA_ERROR", "title": "Invalid Data", "description": "The provided data is invalid or malformed."},

    # Validation errors
    "VALIDATION_MISSING_FIELD": {"category": "VALIDATION_ERROR", "title": "Missing Required Field", "description": "A required field is missing in the input."},
    "VALIDATION_INVALID_VALUE": {"category": "VALIDATION_ERROR", "title": "Invalid Value", "description": "The value provided is invalid."},
    "VALIDATION_TYPE_MISMATCH": {"category": "VALIDATION_ERROR", "title": "Type Mismatch", "description": "The data type does not match the expected type."},

    # Processing errors
    "PROCESSING_FAILED": {"category": "PROCESSING_ERROR", "title": "Processing Failed", "description": "Document processing failed due to an error."},
    "PROCESSING_TIMEOUT": {"category": "PROCESSING_ERROR", "title": "Processing Timeout", "description": "The processing operation timed out."},

    # System errors
    "SYSTEM_MEMORY_ERROR": {"category": "SYSTEM_ERROR", "title": "Memory Error", "description": "Insufficient memory to complete the operation."},
    "SYSTEM_DISK_ERROR": {"category": "SYSTEM_ERROR", "title": "Disk Error", "description": "An error occurred with disk operations."},

    # Network errors
    "NETWORK_CONNECTION_FAILED": {"category": "NETWORK_ERROR", "title": "Connection Failed", "description": "Failed to establish a network connection."},
    "NETWORK_TIMEOUT": {"category": "NETWORK_ERROR", "title": "Network Timeout", "description": "The network operation timed out."},

    # Authentication errors
    "AUTH_INVALID_CREDENTIALS": {"category": "AUTHENTICATION_ERROR", "title": "Invalid Credentials", "description": "The provided credentials are invalid."},
    "AUTH_UNAUTHORIZED": {"category": "AUTHENTICATION_ERROR", "title": "Unauthorized Access", "description": "Access is unauthorized."},

    # Configuration errors
    "CONFIG_MISSING": {"category": "CONFIGURATION_ERROR", "title": "Configuration Missing", "description": "Required configuration is missing."},
    "CONFIG_INVALID": {"category": "CONFIGURATION_ERROR", "title": "Invalid Configuration", "description": "The configuration is invalid."}
}

def get_system_info():
    """Retrieve system information like IP and MAC address."""
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "Unknown"
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 8*6, 8)][::-1])
    except Exception:
        mac = "Unknown"
    return {"ip": ip, "mac": mac}

def format_error(code=None, category=None, message=None, details=None, title=None):
    """Format an error with additional details including timestamp, IP, MAC, etc."""
    if code and code in ERROR_CODES:
        error_info = ERROR_CODES[code]
        category = error_info["category"]
        title = title or error_info["title"]
        message = message or error_info["description"]
    elif not category:
        category = "SYSTEM_ERROR"
    if not title:
        title = "Error"

    system_info = get_system_info()
    timestamp = datetime.datetime.now().isoformat()

    return {
        "code": code,
        "category": category,
        "title": title,
        "message": message,
        "details": details or str(details) if details else None,
        "timestamp": timestamp,
        "ip": system_info["ip"],
        "mac": system_info["mac"]
    }
# Backend Working Documentation Summary

## Project Overview

The Batch Highlighter API is a FastAPI-based backend service that processes and highlights data in PDF and DOCX files based on input Excel/CSV data. It supports both single-column and multi-column PDF layouts with intelligent engine selection.

## Architecture

The system follows a modular architecture with clear separation of concerns:

### Core Components
1. **API Layer**: FastAPI endpoints for file processing, progress tracking, and downloads
2. **Business Logic**: Services for job queue management, background processing, and highlighting
3. **Data Access**: Job repository for persistence and state management
4. **Highlighting Engines**: Specialized engines for PDF and DOCX highlighting
5. **Error Handling**: Custom exceptions, error codes, and exception handlers
6. **Configuration**: Centralized settings management with environment variables

## Key Features

### File Processing
- Support for PDF and DOCX files
- Excel/CSV data input for highlight values
- Multi-column PDF detection and processing
- Real-time progress tracking
- Job queue management with concurrency control

### Highlighting Capabilities
- Single and multi-column PDF highlighting
- DOCX document highlighting
- Custom color selection
- Highlight padding configuration
- Detection of complex table structures

### Job Management
- Job creation and tracking
- Pause/resume functionality
- Job cancellation
- Progress monitoring
- Detailed logging

### Output Generation
- Highlighted PDF/DOCX files
- Matches CSV report
- Unmatched values report
- Combined logs and statistics

## Technology Stack

### Backend Framework
- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and serialization
- **Asyncio**: Asynchronous programming support

### Document Processing
- **PyMuPDF**: PDF processing and highlighting
- **python-docx**: DOCX file manipulation
- **pandas**: Data analysis and Excel/CSV parsing
- **openpyxl**: Excel file handling

### Job Queue and Background Processing
- **asyncio**: Async job processing
- **Redis**: Optional production job queue
- **In-memory queue**: Default development queue

### Configuration and Logging
- **python-dotenv**: Environment variable management
- **python-json-logger**: JSON logging format
- **structlog**: Structured logging

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking

## Running the Application

### Prerequisites
1. Python 3.9+
2. Redis server (for production)
3. Required dependencies (install via `pip install -r requirements.txt`)

### Startup
```bash
# Development mode
cd batch_highlighter_api_integrated
python main.py --host 0.0.0.0 --port 8000 --reload

# Production mode (with Redis)
# Start Redis server first
cd batch_highlighter_api_integrated
python main.py --host 0.0.0.0 --port 8000 --workers 4
```

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

## API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Configuration

Key configuration options can be set via environment variables or `.env` file:
- `HOST`: Server host address
- `PORT`: Server port number
- `WORKERS`: Number of worker processes
- `DEBUG`: Debug mode
- `REDIS_URL`: Redis server URL for job queue
- `HIGHLIGHT_PADDING`: Highlight padding in points

## Error Handling

The system uses structured error codes with categories:
- `FILE_ERROR`: File-related errors
- `DATA_ERROR`: Data processing errors
- `VALIDATION_ERROR`: Input validation errors
- `PROCESSING_ERROR`: Document processing errors
- `SYSTEM_ERROR`: System or unexpected errors

## Conclusion

The Batch Highlighter API provides a robust backend for automated document highlighting with support for various document formats and layouts. The modular architecture ensures maintainability and scalability, making it suitable for both single-instance deployments and distributed processing environments.
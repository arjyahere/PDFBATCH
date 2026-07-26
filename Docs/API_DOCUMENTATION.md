# Batch Highlighter API Documentation

## Overview
This document describes the API endpoints used by the Batch Highlighter application for batch document highlighting and annotation. The API supports processing PDF and DOCX files with values from CSV or Excel data files.

## Base URL
- Local: `http://127.0.0.1:8000`
- Production: Configure via `BASE_URLS` environment variable
- API Version: `v1`
- Full Base Path: `{BASE_URL}/api/v1`

## Root Endpoints

| Endpoint       | Method |     Description                |
|----------------|--------|--------------------------------|
| `/health`      | GET    | Health check with version info |
| `/ready`       | GET    | Readiness probe for containers |
| `/worker-info` | GET    | Get worker process information |

### Health Check (Root)
**GET** `/health`
- Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Readiness Check
**GET** `/ready`
- Response: `{"ready": true, "status": "ready"}`

### Worker Info
**GET** `/worker-info`
- Response:
```json
{
  "pid": 12345,
  "parent_pid": 12340,
  "worker_count": null
}
```

## Endpoints Summary

| Frontend Method    | HTTP Method |     Endpoint                      | Description                    |
|--------------------|-------------|-----------------------------------|--------------------------------|
| `loadColumns()`    | POST        | `/api/v1/misc/load-columns`       | Extract columns from data file |
| `startProcess()`   | POST        | `/api/v1/process`                 | Start batch processing         |
| `_fetchProgress()` | GET         | `/api/v1/progress`                | Get processing progress        |
| `pauseProcess()`   | POST        | `/api/v1/process/{job_id}/pause`  | Pause running job              |
| `resumeProcess()`  | POST        | `/api/v1/process/{job_id}/resume` | Resume paused job              |
| `stopProcess()`    | POST        | `/api/v1/process/{job_id}/cancel` | Cancel job                     |
| `downloadFile()`   | GET         | `/api/v1/download/{filename}`     | Download processed file        |

## Detailed Endpoints

### Health Check
**GET** `/api/v1/misc/health`
- Returns: `{"status": "healthy", "service": "batch-highlighter-api"}`
- Purpose: Frontend uses this to verify server connectivity

### Load Columns
**POST** `/api/v1/misc/load-columns`
- Request: Multipart form with `file` field (CSV or Excel)
- Response: `{"columns": ["col1", "col2", ...]}`
- Purpose: Extract column names from uploaded data file

### Start Processing
**POST** `/api/v1/process`
- Request: Multipart form with:
  - `data_file`: Data file (CSV/Excel) [Required]
  - `documents`: List of document files (PDF/DOCX) [Required]
  - `selected_columns`: Comma-separated column names [Required]
  - `selected_color`: Highlight color (Yellow, Green, Cyan, Pink, Blue, Red) [Default: Yellow]
  - `destination_folder`: Optional output directory
- Response:
```json
{
  "message": "Processing started",
  "job_id": "uuid-string",
  "total_values": N,
  "total_pairs": N,
  "total_files": N,
  "progress_url": "/api/v1/progress",
  "links": {"progress": "/api/v1/progress", "jobs": "/api/v1/process"}
}
```
- Purpose: Start batch document highlighting process

### Get Job Status
**GET** `/api/v1/process/{job_id}`
- Response:
```json
{
  "job_id": "uuid",
  "status": "pending|processing|completed|failed|paused|cancelled",
  "progress": 0-100,
  "created_at": "ISO timestamp",
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp",
  "result": {...},
  "error": "error message if failed"
}
```
- Purpose: Get detailed status of a specific job

### List All Jobs
**GET** `/api/v1/process`
- Response: Array of job status objects (see above)
- Purpose: List all jobs in the queue

### Pause Job
**POST** `/api/v1/process/{job_id}/pause`
- Response:
```json
{
  "message": "Job {job_id} paused successfully",
  "job_id": "uuid",
  "links": {"jobs": "/api/v1/process"}
}
```
- Purpose: Pause a running job
- Error Codes:
  - `JOB_NOT_FOUND`: Job not found
  - `INVALID_STATUS`: Cannot pause job not in processing state

### Resume Job
**POST** `/api/v1/process/{job_id}/resume`
- Response:
```json
{
  "message": "Job {job_id} resumed successfully",
  "job_id": "uuid",
  "links": {"jobs": "/api/v1/process"}
}
```
- Purpose: Resume a paused job
- Error Codes:
  - `JOB_NOT_FOUND`: Job not found
  - `INVALID_STATUS`: Cannot resume job not in paused state

### Cancel Job
**POST** `/api/v1/process/{job_id}/cancel`
- Response:
```json
{
  "message": "Job {job_id} cancelled successfully",
  "job_id": "uuid",
  "links": {"jobs": "/api/v1/process"}
}
```
- Purpose: Cancel a pending, processing, or paused job
- Error Codes:
  - `JOB_NOT_FOUND`: Job not found
  - `INVALID_STATUS`: Cannot cancel job in terminal state

### Get Progress
**GET** `/api/v1/progress`
- Response:
```json
{
  "running": true,
  "paused": false,
  "progress": 50.0,
  "status": "Processing...",
  "job_id": "uuid",
  "start_time": "ISO timestamp",
  "end_time": "ISO timestamp",
  "completed": false,
  "current_file": "filename.pdf",
  "files_processed": 5,
  "total_matches_found": 25,
  "completion_summary": {...},
  "logs": [...],
  "combined_log": "...",
  "not_found_report": "...",
  "output_files": [{"name": "file.pdf", "type": "pdf"}]
}
```
- Purpose: Get real-time progress of current processing

### Get Logs
**GET** `/api/v1/progress/logs?limit=100`
- Query Parameters:
  - `limit`: Maximum number of log entries to return (default: 100)
- Response: Array of log entries
- Purpose: Get processing logs

### List Available Files
**GET** `/api/v1/download/list`
- Response:
```json
{
  "files": [
    {"name": "file.pdf", "size": 1234, "url": "/api/v1/download/file.pdf"}
  ],
  "folder": "output"
}
```
- Purpose: List all available output files

### Download File
**GET** `/api/v1/download/{filename}`
- Response: File download (PDF, CSV, etc.)
- Purpose: Download a processed file
- Note: Automatically finds files with `_1_Highlighted` suffix if exact name not found

## Job Status Values

Jobs can have the following status values:

| Status       | Description                       |
|--------------|-----------------------------------|
| `pending`    | Job is queued but not yet started |
| `processing` | Job is currently being processed  |
| `completed`  | Job completed successfully        |
| `failed`     | Job encountered an error          |
| `paused`     | Job was paused by user            |
| `cancelled`  | Job was cancelled by user         |

## Highlight Colors

Available highlight colors with their RGB values:

| Color  | PDF RGB           | Word Value | DOCX Enum |
|--------|-------------------|------------|-----------|
| Yellow | (1.0, 1.0, 0.2)   | yellow     | yellow    |
| Green  | (0.66, 1.0, 0.33) | green      | green     |
| Cyan   | (0.4, 1.0, 1.0)   | cyan       | cyan      |
| Pink   | (1.0, 0.6, 0.86)  | magenta    | magenta   |
| Blue   | (0.6, 0.85, 1.0)  | blue       | blue      |
| Red    | (1.0, 0.55, 0.55) | red        | red       |

## Frontend Integration

### HighlighterProvider (Flutter)
The frontend uses `HighlighterProvider` class for API communication:

```dart
// Key methods and endpoints
class HighlighterProvider {
  // Load columns from data file
  Future<void> loadColumns()
    // Calls: POST /api/v1/misc/load-columns

  // Start batch processing
  Future<String?> startProcess({String? destinationFolder})
    // Calls: POST /api/v1/process
    // Stores: job_id from response

  // Poll for progress updates
  Future<void> _fetchProgress()
    // Calls: GET /api/v1/progress

  // Pause running job
  Future<String?> pauseProcess()
    // Calls: POST /api/v1/process/{job_id}/pause

  // Resume paused job
  Future<String?> resumeProcess()
    // Calls: POST /api/v1/process/{job_id}/resume

  // Cancel job
  Future<String?> stopProcess()
    // Calls: POST /api/v1/process/{job_id}/cancel

  // Download file
  Future<String?> downloadFile(String fileName)
    // Calls: GET /api/v1/download/{filename}
}
```

### Server Fallback
The frontend supports multiple API servers with automatic failover:
- Configure via `BASE_URLS` environment variable (comma-separated)
- Example: `BASE_URLS=http://127.0.0.1:8000,https://server.example.com`
- Frontend automatically tries next server if current fails

## Configuration

### Environment Variables
```env
# Frontend (.env)
BASE_URLS=http://127.0.0.1:8000,https://server.example.com
API_VERSION=v1
ENVIRONMENT=DEV
```

### Flutter AppConfig
```dart
// Default timeout
static Duration get defaultTimeout => const Duration(seconds=30);

// Upload timeout
static Duration get uploadTimeout => const Duration(seconds=120);

// Download timeout
static Duration get downloadTimeout => const Duration(seconds=60);

// Progress polling interval
static Duration get progressPollingInterval => const Duration(seconds=1);
```

## Error Handling

| HTTP Code |     Code        |     Description                            |
|-----------|-----------------|--------------------------------------------|
| 400       | Various         | Bad request (validation errors)            |
| 400       | INVALID_STATUS  | Operation not valid for current job status |
| 400       | PAUSE_FAILED    | Failed to pause job                        |
| 400       | RESUME_FAILED   | Failed to resume job                       |
| 404       | JOB_NOT_FOUND   | Job not found                              |
| 404       | FILE_NOT_FOUND  | File not found                             |
| 500       | INTERNAL_ERROR  | Internal server error                      |
| 500       | FILE_SAVE_ERROR | Failed to save uploaded file               |
| 500       | DATA_READ_ERROR | Failed to read data file                   |
 
## Running the API

```bash
# Start locally
python main.py

# Or use cluster mode
python run_cluster.py

# API docs available at /docs
# ReDoc available at /redoc
```

## Running the Frontend

```bash
cd flutter_frontend
flutter run
```

## Testing Endpoints

```bash
# Health check (root)
curl http://127.0.0.1:8000/health

# API health check
curl http://127.0.0.1:8000/api/v1/misc/health

# List jobs
curl http://127.0.0.1:8000/api/v1/process

# Get progress
curl http://127.0.0.1:8000/api/v1/progress

# List output files
curl http://127.0.0.1:8000/api/v1/download/list

# Download a file
curl -O http://127.0.0.1:8000/api/v1/download/filename.pdf
```

## Architecture

### Job Queue System
The API uses a concurrent job queue system:
- **Development**: In-memory queue (`InMemoryJobQueue`)
- **Production**: Redis queue (when configured)
- Supports pause, resume, and cancel operations
- Thread-safe state management with asyncio locks

### Processing Flow
1. Client uploads data file + documents via `POST /api/v1/process`
2. Server validates files and extracts values
3. Job is enqueued and processing begins in background
4. Client polls `GET /api/v1/progress` for status updates
5. On completion, files are available for download via `/api/v1/download`

### Supported File Types
| Type       | Extensions        |       Purpose                 |
|------------|-------------------|-------------------------------|
| Data Files | .csv, .xlsx, .xls | Source of values to highlight |
| Documents  | .pdf, .docx       | Documents to be highlighted   |

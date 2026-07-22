# Batch Document Highlighter Workflow

This document explains the complete workflow of the Batch Document Highlighter system, from document submission to result retrieval.

## System Overview

The Batch Document Highlighter is an asynchronous document processing system that:
1. Accepts PDF documents and Excel reference files
2. Matches data from Excel against PDF content
3. Highlights matching terms in the PDF
4. Generates a highlighted PDF and CSV match reports

---

## Architecture Components

### Backend Components ([`batch_highlighter_api_integrated/`](batch_highlighter_api_integrated/))

| Component | Path | Purpose |
|-----------|------|---------|
| **Main API** | [`main.py`](batch_highlighter_api_integrated/main.py) | FastAPI application entry point |
| **Routers** | [`app/routers/`](batch_highlighter_api_integrated/app/routers/) | API endpoints for different operations |
| **Services** | [`app/services/`](batch_highlighter_api_integrated/app/services/) | Business logic for document processing |
| **Repositories** | [`app/repositories/`](batch_highlighter_api_integrated/app/repositories/) | Data persistence layer |
| **Schemas** | [`app/schemas/`](batch_highlighter_api_integrated/app/schemas/) | Pydantic models for request/response |

### Frontend Components ([`flutter_frontend/`](flutter_frontend/))

| Component | Purpose |
|-----------|---------|
| **Providers** | State management for the application |
| **Screens** | UI screens for document upload and progress tracking |

---

## Workflow Steps

### Step 1: Document Upload

**Endpoint:** [`POST /process/upload`](batch_highlighter_api_integrated/app/routers/process_router.py)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Client    │────▶│  Upload     │────▶│  Save to input/ │
│             │     │  Endpoint   │     │  Generate ID    │
└─────────────┘     └─────────────┘     └─────────────────┘
```

**Request Format:**
```json
{
  "pdf_file": "binary",
  "excel_file": "binary",
  "columns": ["column1", "column2"],
  "highlight_all_matches": true
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "queued",
  "message": "Job queued successfully"
}
```

### Step 2: Job Processing (Async)

**Endpoint:** [`GET /progress/{job_id}`](batch_highlighter_api_integrated/app/routers/progress_router.py)

The system uses a queue-based architecture for processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Job Queue System                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │  Queue  │───▶│  Worker 1   │───▶│  Single Column Engine   │  │
│  └─────────┘    └─────────────┘    │  or Multi Column Engine │  │
│                                    └─────────────────────────┘  │
│  Status tracking via Redis/in-memory                            │
└─────────────────────────────────────────────────────────────────┘
```

**Processing States:**
| State | Description |
|-------|-------------|
| `queued` | Job added to queue, waiting for worker |
| `processing` | Worker is actively processing the document |
| `completed` | All highlights applied successfully |
| `failed` | Error occurred during processing |

### Step 3: Document Analysis Engine

**PDF Analysis:** [`pdf_highlighter.py`](batch_highlighter_api_integrated/app/services/pdf_highlighter.py)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   PDF       │────▶│  Extract    │────▶│  Detect Layout  │
│   Input     │     │  Text       │     │  (Single/Multi) │
└─────────────┘     └─────────────┘     └─────────────────┘
```

**Engine Selection:**
- **Single Column Engine:** [`single_column_engine.py`](batch_highlighter_api_integrated/app/services/single_column_engine.py) - For simple, single-column documents
- **Multi Column Engine:** [`multi_column_engine.py`](batch_highlighter_api_integrated/app/services/multi_column_engine.py) - For complex multi-column layouts

### Step 4: Matching Process

**Excel Matching:** [`docx_highlighter.py`](batch_highlighter_api_integrated/app/services/docx_highlighter.py)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Excel     │────▶│  Parse      │────▶│  Find in PDF    │
│   Reference │     │  Columns    │     │  Text & Coords  │
└─────────────┘     └─────────────┘     └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  Record Match   │
                                    │  (Matches.csv)  │
                                    └─────────────────┘
```

### Step 5: Result Download

**Endpoints:**
- [`GET /download/pdf/{job_id}`](batch_highlighter_api_integrated/app/routers/download_router.py) - Download highlighted PDF
- [`GET /download/csv/{job_id}`](batch_highlighter_api_integrated/app/routers/download_router.py) - Download match report

---

## File Structure

```
batch_highlighter_api_integrated/
├── input/                    # Uploaded files temporarily stored here
│   ├── {job_id}_document.pdf
│   └── {job_id}_reference.xlsx
├── output/                   # Processed results
│   ├── {job_id}_Highlighted.pdf
│   ├── {job_id}_Matches.csv
│   └── {job_id}_Missing_values.csv
├── logs/                     # Application logs
│   └── app.log
└── app/
    ├── routers/
    │   ├── process_router.py    # Upload & submit jobs
    │   ├── progress_router.py   # Job status queries
    │   └── download_router.py    # Result downloads
    └── services/
        ├── job_queue.py          # Queue management
        ├── queue_worker.py        # Background workers
        ├── pdf_highlighter.py    # PDF processing
        ├── single_column_engine.py
        └── multi_column_engine.py
```

---

## API Endpoints Summary

### Process Router ([`process_router.py`](batch_highlighter_api_integrated/app/routers/process_router.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process/upload` | Upload PDF + Excel for processing |
| `POST` | `/process` | Submit job with file paths |
| `DELETE` | `/process/{job_id}` | Cancel/delete a job |

### Progress Router ([`progress_router.py`](batch_highlighter_api_integrated/app/routers/progress_router.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/progress/{job_id}` | Get job status and progress % |
| `GET` | `/progress` | List all jobs |

### Download Router ([`download_router.py`](batch_highlighter_api_integrated/app/routers/download_router.py))

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/download/pdf/{job_id}` | Download highlighted PDF |
| `GET` | `/download/csv/{job_id}` | Download matches CSV |
| `GET` | `/download/missing/{job_id}` | Download missing values CSV |

---

## Running the System

### Start API Server
```bash
cd batch_highlighter_api_integrated
python main.py
```

### Start Worker Cluster (Optional)
```bash
python run_cluster.py --workers 4
```

### Start Background Workers Only
```bash
cd batch_highlighter_api_integrated
# On Windows
start_cluster.bat
# On Linux/macOS
bash start_cluster.sh
```

### Clear Memory (Input/Output Folders)
```bash
# On Windows - Double-click or run:
clean_memory.bat
```

---

## Error Handling

The system uses standardized error codes defined in [`error_codes.py`](batch_highlighter_api_integrated/app/core/error_codes.py):

| Error Code | Meaning |
|------------|---------|
| `PDF_READ_ERROR` | Failed to read/parse PDF |
| `EXCEL_READ_ERROR` | Failed to read Excel file |
| `NO_MATCHES_FOUND` | No matching terms found |
| `JOB_NOT_FOUND` | Invalid job ID |
| `PROCESSING_FAILED` | Generic processing error |

---

## Frontend Integration

The Flutter frontend uses the [`HighlighterProvider`](flutter_frontend/lib/providers/highlighter_provider.dart) for state management:

```dart
// Workflow in Flutter:
1. Upload files via multipart request
2. Poll /progress/{job_id} for status updates
3. Navigate to ProgressScreen during processing
4. Download results when completed
```

See [`progress_screen.dart`](flutter_frontend/lib/screens/progress_screen.dart) for the progress tracking UI implementation.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Job stuck in `queued` | Ensure worker process is running |
| Empty matches CSV | Check Excel column names match request |
| PDF not highlighting | Verify PDF text extraction worked |
| High memory usage | Reduce batch size or worker count |

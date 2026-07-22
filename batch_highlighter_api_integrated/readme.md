# Batch Highlighter API

A **FastAPI-based backend system** to match **values from data files** (CSV/Excel) against **PDF/DOCX documents** and automatically **highlight matching entries** with full progress tracking and safe output handling.

------------------------------------------------------------------------

## Overview

This API allows you to upload:
- A **CSV or Excel file** containing values to search for
- One or more **PDF or DOCX documents**

The system will:
- Extract column values from the data file
- Perform **robust matching** in documents
- **Highlight matching text** directly in the documents
- Store processed files safely in an **output folder**
- Provide **live progress tracking** during processing
- Support **pause/resume/cancel** operations

This solution is optimized for **bulk document verification and annotation workflows**.

------------------------------------------------------------------------

## Key Features

- CSV/Excel-based value matching
- Multi-column support (search for 1 or 2 columns)
- Multiple highlight colors (Yellow, Green, Cyan, Pink, Blue, Red)
- Global fallback matching for difficult documents
- PDF/DOCX overwrite protection
- Background task processing (non-blocking)
- Pause / Resume / Cancel support
- Output auto-save to `/output` folder
- REST API-based architecture
- **Load Balancing with Multiple Workers**
- **Job Queue System** for concurrent processing

------------------------------------------------------------------------

## Technology Stack

| Component          |   Technology     |
|--------------------|------------------|
| Language           | Python 3.9+      |
| API Framework      | FastAPI          |
| PDF Processing     | PyMuPDF (fitz)   |
| DOCX Processing    | python-docx      |
| Excel/CSV Handling | Pandas, OpenPyXL |
| Server             | Uvicorn          |
| Background Tasks   | asyncio Queue    |
| Load Balancing     | Uvicorn Workers  |

------------------------------------------------------------------------

## Project Structure

```
project_root/
│
├── app/
│   ├── __init__.py
│   ├── api.py                           # Application entry point (FastAPI app)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── logging_config.py            # Logging configuration
│   │   └── settings.py                  # Application settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Core configuration
│   │   ├── error_codes.py               # Error code definitions
│   │   ├── exception_handlers.py        # Custom exception handlers
│   │   ├── exceptions.py                # Custom exceptions
│   │   ├── state.py                     # Global state & progress tracking
│   │   └── utils.py                     # Utility functions
│   ├── dependencies/
│   │   ├── __init__.py
│   │   └── service_factory.py           # Dependency injection factory
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── job_repository.py            # Job repository
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── download_router.py           # Download endpoints
│   │   ├── misc_router.py               # Miscellaneous endpoints
│   │   ├── process_router.py            # Process/execute endpoints
│   │   └── progress_router.py           # Progress tracking endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common_schemas.py            # Common Pydantic schemas
│   │   └── process_schemas.py           # Process-related schemas
│   └── services/
│       ├── __init__.py
│       ├── docx_highlighter.py          # DOCX highlighting logic
│       ├── job_queue.py                 # Job queue management
│       ├── multi_column_engine.py       # Multi-column PDF processing
│       ├── pdf_highlighter.py           # Core PDF processing logic
│       ├── pdf_highlighter_decider.py   # PDF processing decider
│       ├── queue_worker.py              # Queue worker
│       ├── single_column_engine.py      # Single-column PDF processing
│       └── worker.py                    # Worker implementation
│
├── input/                               # Input files directory
├── output/                              # Processed output files
├── logs/                                # Application logs
├── .env                                 # Environment variables
├── requirements.txt                     # Python dependencies
├── run_cluster.py                       # Advanced cluster manager with load balancer
├── start_cluster.bat                    # Windows startup script
├── start_cluster.sh                     # Linux/Mac startup script
├── main.py                              # Main application entry
├── API_DOCUMENTATION.md                 # API documentation
└── README.md                            # Project documentation
```

------------------------------------------------------------------------

## Installation & Setup

### 1. Create Virtual Environment

```bash
py -m venv .venv
# or
python -m venv .venv
```

Activate it:

```bash
# Linux / Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Running the Server

### Single Instance (Development)

```bash
python main.py
```

Or with auto-reload:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Multiple Workers (Production)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 8
```

### Using Batch Script (Windows)

```bash
start_cluster.bat
```

### Using Shell Script (Linux/Mac)

```bash
chmod +x start_cluster.sh
./start_cluster.sh
```

### Advanced Cluster with Load Balancer

```bash
python run_cluster.py
```

This starts multiple API instances on different ports with a built-in round-robin load balancer.

------------------------------------------------------------------------

## Configuration

Edit the `.env` file to configure:

```env
# Number of worker processes (default: 8)
WORKERS=8

# Main port for the load balancer
PORT=8000

# Environment (production enables all workers)
ENVIRONMENT=development
```

------------------------------------------------------------------------

## Verification

### Check Server Status

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "healthy", "version": "1.0.0", "timestamp": "2024-01-01T00:00:00"}
```

### Check API Health

```bash
curl http://localhost:8000/api/v1/misc/health
```

### Check Active Worker Processes (Windows)

```bash
tasklist | findstr uvicorn
```

### Check Active Worker Processes (Linux/Mac)

```bash
ps aux | grep uvicorn
```

------------------------------------------------------------------------

## Server Access

|     Endpoint                         |   Description       |
|--------------------------------------|---------------------|
| `http://127.0.0.1:8000`              | Main API            |
| `http://127.0.0.1:8000/docs`         | Swagger API Docs    |
| `http://127.0.0.1:8000/redoc`        | ReDoc Documentation |
| `http://127.0.0.1:8000/openapi.json` | OpenAPI Schema      |

------------------------------------------------------------------------

## API Workflow

1. Upload data file (CSV/Excel) with values to search
2. Upload one or more documents (PDF/DOCX)
3. Specify column(s) to use for matching
4. Select highlight color
5. Start processing
6. Monitor progress via API
7. Download highlighted documents

------------------------------------------------------------------------

## Supported File Types

| Type       | Extensions        | Purpose                       |
|------------|-------------------|-------------------------------|
| Data Files | .csv, .xlsx, .xls | Source of values to highlight |
| Documents  | .pdf, .docx       | Documents to be highlighted   |

## Highlight Colors

| Color  | PDF RGB           |        Description          |
|--------|-------------------|-----------------------------|
| Yellow | (1.0, 1.0, 0.2)   | Default highlight           |
| Green  | (0.66, 1.0, 0.33) | Secondary highlight         |
| Cyan   | (0.4, 1.0, 1.0)   | Tertiary highlight          |
| Pink   | (1.0, 0.6, 0.86)  | Alternative highlight       |
| Blue   | (0.6, 0.85, 1.0)  | Alternative highlight       |
| Red    | (1.0, 0.55, 0.55) | Warning/important highlight |

------------------------------------------------------------------------

## Output Handling

- If **no destination folder is provided**, output defaults to:
  ```
  /output
  ```
- Duplicate file names are **automatically renamed**
- Original documents are **never overwritten**
- Processed files have `_1_Highlighted` suffix

------------------------------------------------------------------------

## Job Management

### Job States

| State        | Description                       |
|--------------|-----------------------------------|
| `pending`    | Job is queued but not yet started |
| `processing` | Job is currently being processed  |
| `completed`  | Job completed successfully        |
| `failed`     | Job encountered an error          |
| `paused`     | Job was paused by user            |
| `cancelled`  | Job was cancelled by user         |

### Operations

- **Pause**: Pause a running job
- **Resume**: Resume a paused job
- **Cancel**: Cancel a pending, processing, or paused job

------------------------------------------------------------------------

## Safety Features

- Document overwrite protection
- Invalid file format detection
- Empty column validation
- Corrupt document auto-skip
- Fault-tolerant background execution
- Path traversal protection

------------------------------------------------------------------------

## Performance Notes

- Optimized for **large documents (500+ pages)**
- Handles **10,000+ matches efficiently**
- Chunk-based document parsing
- Asynchronous background processing
- **Multiple workers for horizontal scaling**
- **In-memory job queue** (Redis available for production)

------------------------------------------------------------------------

## Requirements

- Python 3.9 or higher
- Minimum 4GB RAM recommended
- Windows / Linux / Mac compatible

------------------------------------------------------------------------

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API endpoint documentation.

------------------------------------------------------------------------

## Frontend Integration

This backend is designed to work with the Flutter frontend. See `../flutter_frontend/README.md` for frontend setup instructions.

------------------------------------------------------------------------

## License

This project is licensed for **internal organizational use only**.

------------------------------------------------------------------------

*Fast. Reliable. Automated Document Highlighting System.*

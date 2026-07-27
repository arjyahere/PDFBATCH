# PDFBATCH — Batch Highlighter

Automatically find values from a CSV/Excel sheet inside a batch of PDF/DOCX documents, highlight the matches, and export reports. It replaces slow, error-prone manual document review with a repeatable API-driven workflow.

---

## What it does

1. You upload a **data file** (CSV or XLSX) containing the values to look for, plus one or more **documents** (PDF or DOCX).
2. The backend extracts the values from the selected column(s) and searches each document.
3. Matches are **highlighted directly in the document** using your chosen color.
4. The results are saved to `output/` alongside a **CSV report** of matched and missing values.
5. The web UI shows live progress while the job runs in the background.

Original documents are never overwritten — processed copies go to a separate output folder.

---

## How it works

```
Flutter web UI  ──HTTP──▶  FastAPI backend  ──▶  job queue / worker
     │                          │                      │
     │                          │                      ├─ extract text (PyMuPDF / python-docx)
     │                          │                      ├─ match values (pandas / openpyxl)
     │                          │                      └─ write highlighted files + CSV
     │                          │
     └── polls progress ────────┘                ──▶  output/
```

- **Backend** (`batch_highlighter_api_integrated/`) — Python 3.9+, FastAPI, PyMuPDF, python-docx, pandas/openpyxl, Uvicorn. Routes live under `/api/v1/` (`/process`, `/progress`, `/download`, `/misc`); interactive API docs at `/docs`.
- **Frontend** (`flutter_frontend/`) — Flutter app compiled to web, served locally on port 8001. Talks to the API on port 8000.
- **Processing** — uploads go to `input/` with a unique job ID, a background worker processes the batch, and results land in `output/`.

---

## Advantages

- **Fast batch processing** — review hundreds of documents in minutes instead of hours.
- **Consistent, auditable results** — the same matching rules apply to every document, with a CSV trail of what was and wasn't found.
- **Multi-format support** — CSV/XLSX in, PDF/DOCX out; one or two search columns.
- **Visual clarity** — up to six highlight colors so different value sets are easy to distinguish.
- **Non-blocking UI** — jobs run in the background with live progress, so you can watch or walk away.
- **Cross-platform** — one Flutter frontend targets web, Windows, macOS, Linux, iOS and Android.
- **Safe by design** — originals preserved, unique job IDs, input validation.
- **Scriptable** — a documented REST API, so the tool can be driven from other systems, not just the UI.

---

## Quick start (Windows)

```bat
Scripts\setup_all.bat        :: create .venv, install requirements, flutter pub get, build web
Scripts\start.bat            :: launch frontend + backend and open the app
```

The app opens at `http://localhost:8001`; API docs at `http://localhost:8000/docs`.

Useful maintenance scripts (all in `Scripts/`):

| Script | Purpose |
|---|---|
| `setup_all.bat` / `setup_all.sh` | Interactive one-shot setup (venv, pip, Flutter build) |
| `start.bat` / `start_cluster.bat` | Launch the stack locally / with multiple workers |
| `cleanup_all.bat` / `cleanup_all.sh` | Remove caches, venvs, builds and logs (keeps `input/` and `output/`) |
| `clean_python_cache.bat` | Remove Python bytecode and test caches |
| `remove_venv.bat` | Delete the Python virtual environments |
| `flutter_pub_clean.bat` | Run `flutter pub clean` |

`setup_all.sh` and `cleanup_all.sh` are the macOS/Linux equivalents. Set `FLUTTER_ROOT` or put Flutter on `PATH` first.

---

## Repository layout

```
Docs/                                  Guides and API reference
Scripts/                               Setup, launch and cleanup scripts
batch_highlighter_api_integrated/      FastAPI backend
  app/api.py                           App and /api/v1 wiring
  app/routers/                         Process, progress, download, misc endpoints
  app/services/                        Engine and job queue
  input/  output/                      Runtime data (git-ignored)
flutter_frontend/                      Flutter client
  build/web/                           Built web app served by start.bat
```

Runtime data (`input/`, `output/`, `logs/`, databases) and secrets (`*.env`) are git-ignored.

---

## Documentation

- [Tool documentation](Docs/TOOL_DOCUMENTATION.md) — full workflow and feature guide
- [API reference](Docs/API_DOCUMENTATION.md) — endpoints and payloads
- [Workflow](Docs/WORKFLOW.md) — step-by-step processing details
- [Backend working notes](Docs/BACKEND_WORKING.md) and [summary](Docs/BACKEND_SUMMARY.md)

---

## Limitations

- Best with text-based PDFs; scanned documents need OCR first.
- Matching is exact-value based, not fuzzy — formatting must agree between the data file and documents.
- Very large documents or batches need more RAM/time.
- Requires Python and a Flutter SDK to build from source; the prebuilt web bundle is not committed.

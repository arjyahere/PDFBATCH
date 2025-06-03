# ✅ PDF UAN / ESI Highlighter API

A **FastAPI-based backend system** to match **UAN / ESI numbers from
Excel files** against **PDF documents** and automatically **highlight
matching entries** in the PDFs with full progress tracking and safe
output handling.

------------------------------------------------------------------------

## 📌 Overview

This API allows you to upload: - An **Excel file** containing UAN or ESI
numbers - One or more **PDF files**

The system will: - Automatically **detect the correct UAN/ESI column** -
Perform **robust matching (including split-digit recovery)** -
**Highlight matching rows directly inside the PDF** - Store the
processed files safely in an **auto-created output folder** - Provide
**live progress tracking** during processing

This solution is optimized for **bulk PF & ESIC verification and
compliance workflows**.

------------------------------------------------------------------------

## 🚀 Key Features

✅ Excel-based number matching\
✅ Automatic UAN / ESI column detection\
✅ 100% UAN split-digit recovery logic\
✅ Global fallback matching for difficult PDFs\
✅ PDF overwrite protection\
✅ Background task processing (non-blocking)\
✅ Pause / Resume support\
✅ Output auto-save to `/output` folder\
✅ REST API-based architecture

------------------------------------------------------------------------

## 🛠 Technology Stack

  Component          Technology
  ------------------ -------------------------
  Language           Python 3.9+
  API Framework      FastAPI
  PDF Processing     PyMuPDF (fitz)
  Excel Handling     Pandas, OpenPyXL
  Server             Uvicorn
  Background Tasks   FastAPI BackgroundTasks

------------------------------------------------------------------------

## 📁 Project Structure

``` text
project_root/
│
├── app/
│   ├── core/
│   │   ├── utils.py           # Utility functions
│   │   └── state.py           # Global state & progress tracking
│   ├── services/
│   │   └── pdf_highlighter.py # Core PDF processing logic
│   ├── routes/
│   │   └── api.py             # API endpoints
│   └── main.py                # Application entry point
│
├── output/                    # Auto-created highlighted PDFs
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

------------------------------------------------------------------------

## ⚙️ Installation & Setup

### 1️⃣ Create Virtual Environment

``` bash
py -m venv .venv

python -m venv .venv
```

Activate it:

``` bash
# Linux / Mac
source .venv/bin/activate

# Windows

.venv\Scripts\activate
```

------------------------------------------------------------------------

### 2️⃣ Install Dependencies

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

### 3️⃣ Run the Server

``` bash
uvicorn app.main:app --reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
cloudflared tunnel --url http://localhost:8000


flutter clean
flutter pub get
flutter build web

flutter run -d web-server --web-port=8080 --web-hostname=0.0.0.0 
or

cd flutter_frontend\build\web
python -m http.server 8080


cloudflared tunnel --url http://localhost:8080


```

------------------------------------------------------------------------

### 4️⃣ Server Access

``` text
http://127.0.0.1:8000
```

Swagger API Docs:

``` text
http://127.0.0.1:8000/docs
```

------------------------------------------------------------------------

## 🔁 API Workflow

1.  Upload Excel file with UAN/ESI numbers
2.  Upload one or more PDFs
3.  System auto-detects matching column
4.  Matching numbers are located inside the PDFs
5.  Matched rows are highlighted
6.  Processed PDFs are saved inside `/output` folder
7.  Live progress can be monitored via API

------------------------------------------------------------------------

## 📂 Output Handling

-   If **no destination folder is provided**, output defaults to:

    ``` text
    /output
    ```

-   Duplicate file names are **automatically renamed**

-   Original PDFs are **never overwritten**

------------------------------------------------------------------------

## ⏯ Pause & Resume Support

-   Processing can be paused via API
-   Resume processing without re-uploading files
-   State is maintained globally using `state.py`

------------------------------------------------------------------------

## 🔐 Safety Features

-   PDF overwrite protection
-   Invalid file format detection
-   Empty column validation
-   Corrupt PDF auto-skip
-   Fault-tolerant background execution

------------------------------------------------------------------------

## 📈 Performance Notes

-   Optimized for **large PDFs (500+ pages)**
-   Handles **10,000+ UAN matches efficiently**
-   Chunk-based PDF parsing
-   Asynchronous background processing

------------------------------------------------------------------------

## ✅ Requirements

-   Python 3.9 or higher
-   Minimum 4GB RAM recommended
-   Windows / Linux / Mac compatible

------------------------------------------------------------------------

## 🧩 Future Enhancements (Optional)

-   Web-based dashboard (React / Flutter)
-   Role-based authentication
-   Batch Excel upload
-   OCR for scanned PDFs
-   Cloud storage support (S3 / Azure)

------------------------------------------------------------------------

## 👨‍💻 Author

Developed for internal payroll & statutory compliance automation.

------------------------------------------------------------------------

## 📃 License

This project is licensed for **internal organizational use only**.

------------------------------------------------------------------------

✅ *Fast. Reliable. Automated UAN & ESI PDF Highlighting System.*

@echo off
REM Start the Batch Highlighter API with multiple worker instances
REM Uses Uvicorn's built-in multiprocessing

setlocal

REM Resolve repo root from this script's location, then work in the backend folder
cd /d "%~dp0.."
set "ROOT=%CD%"
set "BACKEND_PATH=%ROOT%\batch_highlighter_api_integrated"
cd /d "%BACKEND_PATH%"

REM Load environment variables from .env file
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
        set "%%a=%%b"
    )
)

REM Default values
if not defined HOST set HOST=0.0.0.0
if not defined PORT set PORT=8000
if not defined WORKERS set WORKERS=3

REM Uvicorn is installed in the backend virtual environment
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
echo ""              Batch Highlighter API Cluster Mode             ""
echo """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
echo.
echo Starting Uvicorn with %WORKERS% workers on %HOST%:%PORT%
echo Backend: %BACKEND_PATH%
echo.

REM Start the server with multiple workers using configured HOST and PORT
uvicorn main:app --host %HOST% --port %PORT% --workers %WORKERS% --no-reload

endlocal

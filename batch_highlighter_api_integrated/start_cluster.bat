@echo off
REM Start the Batch Highlighter API with multiple worker instances
REM Uses Uvicorn's built-in multiprocessing

setlocal

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Load environment variables from .env file
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
        set "%%a=%%b"
    )
)

REM Default values
if not defined PORT set PORT=8000

echo """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
echo ""              Batch Highlighter API Cluster Mode             ""
echo """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
echo.
echo Starting Uvicorn with %WORKERS% workers on %HOST%:%PORT%
echo.

REM Start the server with multiple workers using configured HOST and PORT
uvicorn main:app --reload --host %HOST% --port %PORT%

endlocal

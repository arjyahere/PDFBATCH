@echo off
setlocal
REM Clear input and output folders of the backend (not the folder this script runs from)

cd /d "%~dp0..\batch_highlighter_api_integrated"
set "BACKEND_PATH=%CD%"

echo ========================================
echo    Clearing Input and Output Folders
echo ========================================
echo Target: %BACKEND_PATH%
echo.

REM Clear input folder
if exist "input\*" (
    echo [1/2] Clearing input folder...
    del /q "input\*"
    for /d %%i in ("input\*") do rmdir /s /q "%%i" 2>nul
    echo        Input folder cleared successfully!
) else (
    echo        Input folder is already empty or does not exist.
)

echo.

REM Clear output folder
if exist "output\*" (
    echo [2/2] Clearing output folder...
    del /q "output\*"
    for /d %%i in ("output\*") do rmdir /s /q "%%i" 2>nul
    echo        Output folder cleared successfully!
) else (
    echo        Output folder is already empty or does not exist.
)

echo.
echo ========================================
echo    Memory cleared successfully!
echo ========================================
echo.
pause

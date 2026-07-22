@echo off
REM Clear Memory Batch Script
REM This script clears all files from input and output folders

echo ========================================
echo    Clearing Input and Output Folders
echo ========================================
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

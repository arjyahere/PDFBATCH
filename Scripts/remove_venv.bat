@echo off
setlocal
REM Remove the Python virtual environments used by this repo

cd /d "%~dp0.."
set "ROOT=%CD%"

echo ========================================
echo    Removing Python virtual environments
echo ========================================
echo Root: %ROOT%
echo.

set "COUNT=0"
for %%V in ("%ROOT%\.venv" "%ROOT%\venv" "%ROOT%\batch_highlighter_api_integrated\.venv" "%ROOT%\batch_highlighter_api_integrated\venv") do (
    if exist "%%~V" (
        echo Removing %%~V
        rmdir /s /q "%%~V" 2>nul
        set /a COUNT+=1
    )
)

echo.
echo Virtual environments removed: %COUNT%
echo Recreate with: python -m venv batch_highlighter_api_integrated\.venv
echo ========================================
echo.
pause

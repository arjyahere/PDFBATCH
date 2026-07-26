@echo off
setlocal
REM Remove Python bytecode and test caches anywhere under the repo

cd /d "%~dp0.."
set "ROOT=%CD%"

echo ========================================
echo    Cleaning Python caches
echo ========================================
echo Root: %ROOT%
echo.

set "COUNT=0"
for /d /r "%ROOT%" %%d in (__pycache__ .pytest_cache .mypy_cache .ruff_cache) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        set /a COUNT+=1
    )
)

for /r "%ROOT%" %%f in (*.pyc *.pyo) do del /q "%%f" 2>nul

echo.
echo Python caches removed: %COUNT%
echo ========================================
echo.
pause

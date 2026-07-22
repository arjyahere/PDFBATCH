@echo off
setlocal EnableDelayedExpansion

title Full Stack Launcher (Flutter + FastAPI)
color 0A

:: =========================================================
:: CONFIG
:: =========================================================
set "FRONTEND_PATH=C:\PROJECT_WORK\PFD\V3-1\flutter_frontend\build\web"
set "BACKEND_PATH=C:\PROJECT_WORK\PFD\V3-1\batch_highlighter_api_integrated"

set "FRONTEND_PORT=8001"
set "API_PORT=8000"

:: =========================================================
:: HEADER
:: =========================================================
cls
echo =========================================================
echo              FULL APPLICATION STACK STARTER
echo =========================================================
echo.
echo FRONTEND PATH : %FRONTEND_PATH%
echo BACKEND PATH  : %BACKEND_PATH%
echo FRONTEND PORT : %FRONTEND_PORT%
echo API PORT      : %API_PORT%
echo.

:: =========================================================
:: CHECK WINDOWS TERMINAL
:: =========================================================
echo [1/8] Checking Windows Terminal...

where wt >nul 2>&1

if errorlevel 1 (
    echo.
    echo ERROR: Windows Terminal is not installed
    echo Install from Microsoft Store:
    echo https://aka.ms/terminal
    echo.
    pause
    exit /b 1
)

echo [OK] Windows Terminal found
echo.

:: =========================================================
:: VALIDATE PATHS
:: =========================================================
echo [2/8] Validating paths...

if not exist "%FRONTEND_PATH%" (
    echo.
    echo ERROR: Frontend path not found
    echo %FRONTEND_PATH%
    echo.
    pause
    exit /b 1
)

if not exist "%BACKEND_PATH%" (
    echo.
    echo ERROR: Backend path not found
    echo %BACKEND_PATH%
    echo.
    pause
    exit /b 1
)

if not exist "%BACKEND_PATH%\.venv\Scripts\activate.bat" (
    echo.
    echo ERROR: Python virtual environment not found
    echo %BACKEND_PATH%\.venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

echo [OK] All paths verified
echo.

:: =========================================================
:: CLEAN OLD PORTS
:: =========================================================
echo [3/8] Cleaning old processes...

for %%P in (%FRONTEND_PORT% %API_PORT%) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P') do (
        taskkill /PID %%A /F >nul 2>&1
    )
)

timeout /t 2 >nul

echo [OK] Old processes cleaned
echo.

:: =========================================================
:: START WINDOWS TERMINAL
:: =========================================================
echo [4/8] Launching Windows Terminal...

start "" wt ^
new-tab --title "Flutter Frontend" ^
cmd /k "cd /d \"%FRONTEND_PATH%\" && echo. && echo ======================================== && echo        FLUTTER FRONTEND SERVER && echo ======================================== && echo. && python -u -m http.server %FRONTEND_PORT%" ^
; ^
new-tab --title "FastAPI Backend" ^
cmd /k "cd /d \"%BACKEND_PATH%\" && call .venv\Scripts\activate.bat && echo. && echo ======================================== && echo           FASTAPI BACKEND && echo ======================================== && echo. && python -u -m uvicorn main:app --reload --host 0.0.0.0 --port %API_PORT%"

timeout /t 6 >nul

:: =========================================================
:: VERIFY FRONTEND
:: =========================================================
echo [5/8] Verifying frontend...

set "FRONTEND_OK=0"

netstat -ano | findstr ":%FRONTEND_PORT%" >nul

if not errorlevel 1 (
    set "FRONTEND_OK=1"
    echo [OK] Frontend running on:
    echo http://localhost:%FRONTEND_PORT%
) else (
    echo [FAIL] Frontend failed to start
)

echo.

:: =========================================================
:: VERIFY BACKEND
:: =========================================================
echo [6/8] Verifying backend...

set "API_OK=0"

netstat -ano | findstr ":%API_PORT%" >nul

if not errorlevel 1 (
    set "API_OK=1"
    echo [OK] Backend running on:
    echo http://localhost:%API_PORT%
) else (
    echo [FAIL] Backend failed to start
)

echo.

:: =========================================================
:: OPEN APPLICATION
:: =========================================================
echo [7/8] Opening application...

if "!FRONTEND_OK!"=="1" (
    start http://localhost:%FRONTEND_PORT%
)

echo.

:: =========================================================
:: FINAL STATUS
:: =========================================================
echo [8/8] Final Status
echo.

echo =========================================================

if "!FRONTEND_OK!"=="1" if "!API_OK!"=="1" (
    echo SUCCESS: FULL STACK STARTED SUCCESSFULLY
) else (
    echo WARNING: SOME SERVICES FAILED
)

echo =========================================================
echo.
echo FRONTEND:
echo http://localhost:%FRONTEND_PORT%
echo.
echo BACKEND:
echo http://localhost:%API_PORT%
echo.
echo API DOCS:
echo http://localhost:%API_PORT%/docs
echo =========================================================
echo.

pause   
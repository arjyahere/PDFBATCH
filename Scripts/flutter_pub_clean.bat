@echo off
setlocal
REM Delete Flutter build artifacts and cached dependencies for the frontend

cd /d "%~dp0..\flutter_frontend"

if not exist pubspec.yaml (
    echo ERROR: pubspec.yaml not found in %CD%
    pause
    exit /b 1
)

REM Locate Flutter dynamically: env var, PATH, then common SDK locations
set "FLUTTER_CMD="
if defined FLUTTER_ROOT if exist "%FLUTTER_ROOT%\bin\flutter.bat" set "FLUTTER_CMD=%FLUTTER_ROOT%\bin\flutter.bat"
if not defined FLUTTER_CMD (
    for /f "delims=" %%F in ('where flutter 2^>nul') do if not defined FLUTTER_CMD set "FLUTTER_CMD=%%F"
)
if not defined FLUTTER_CMD (
    for %%D in ("C:\flutter" "C:\src\flutter" "C:\tools\flutter" "%LOCALAPPDATA%\flutter" "%USERPROFILE%\flutter" "D:\flutter" "%ROOT%\flutter") do (
        if not defined FLUTTER_CMD if exist "%%~D\bin\flutter.bat" set "FLUTTER_CMD=%%~D\bin\flutter.bat"
    )
)
if not defined FLUTTER_CMD (
    echo ERROR: Flutter SDK not found. Set FLUTTER_ROOT or add flutter to PATH.
    pause
    exit /b 1
)

echo ========================================
echo    Flutter pub clean
echo ========================================
echo Directory: %CD%
echo Using Flutter: %FLUTTER_CMD%
echo.
call "%FLUTTER_CMD%" pub clean

echo.
echo ========================================
echo.
pause

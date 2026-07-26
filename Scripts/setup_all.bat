@echo off
setlocal EnableDelayedExpansion
title Project Setup CLI

cd /d "%~dp0.."
set "ROOT=%CD%"
set "BACKEND=%ROOT%\batch_highlighter_api_integrated"
set "FRONTEND=%ROOT%\flutter_frontend"
set "PROMPT_TIMEOUT=20"
set "FAILED=0"

cls
echo ============================================================
echo                    PROJECT SETUP CLI
echo ============================================================
echo  Root     : %ROOT%
echo  Backend  : %BACKEND%
echo  Frontend : %FRONTEND%
echo.
echo  Prompts auto-continue in %PROMPT_TIMEOUT%s with the default choice.
echo.

if not exist "%BACKEND%\requirements.txt" (
    echo  [ERROR] requirements.txt not found in %BACKEND%
    timeout /t 8 >nul
    exit /b 1
)
if not exist "%FRONTEND%\pubspec.yaml" (
    echo  [ERROR] pubspec.yaml not found in %FRONTEND%
    timeout /t 8 >nul
    exit /b 1
)

set "PY_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"
if not defined PY_CMD (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)
if not defined PY_CMD (
    echo  [ERROR] Python not found on PATH
    timeout /t 8 >nul
    exit /b 1
)

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

echo  Detected Python : %PY_CMD%
if defined FLUTTER_CMD (
    echo  Detected Flutter: %FLUTTER_CMD%
) else (
    echo  Detected Flutter: NOT FOUND - steps 3 and 4 cannot run
)
echo.
echo  Setup steps:
echo    1. Create Python virtual environment (.venv)
echo    2. Install Python requirements (pip)
echo    3. Fetch Flutter packages (flutter pub get)
echo    4. Build Flutter web (flutter build web)
echo.

for %%S in (1 2 3 4) do (
    echo ------------------------------------------------------------
    call :describe %%S
    choice /c YNSQ /n /t %PROMPT_TIMEOUT% /d Y /m "  Action [Y]es / [N]o / [S]kip rest / [Q]uit : "
    set "CH=!ERRORLEVEL!"
    if !CH!==4 goto :quit
    if !CH!==3 goto :finish
    if !CH!==1 (
        call :step%%S
        if errorlevel 1 (
            set "FAILED=1"
            choice /c CQ /n /t %PROMPT_TIMEOUT% /d C /m "  Step failed. [C]ontinue / [Q]uit : "
            if !ERRORLEVEL!==2 goto :quit
        )
    ) else (
        echo  [SKIPPED]
    )
)
goto :finish

:describe
if "%1"=="1" echo  Step 1/4 : Create Python virtual environment
if "%1"=="2" echo  Step 2/4 : Install Python dependencies from requirements.txt
if "%1"=="3" echo  Step 3/4 : Fetch Flutter packages
if "%1"=="4" echo  Step 4/4 : Build Flutter web bundle
if "%1"=="3" if not defined FLUTTER_CMD echo            ^(Flutter SDK not found^)
if "%1"=="4" if not defined FLUTTER_CMD echo            ^(Flutter SDK not found^)
exit /b 0

:step1
if not exist "%BACKEND%\.venv\Scripts\python.exe" goto :createvenv
"%BACKEND%\.venv\Scripts\python.exe" -c "import sys" >nul 2>&1
if errorlevel 1 goto :brokenvenv
echo  .venv already exists and works - nothing to do
exit /b 0
:brokenvenv
echo  .venv is broken - recreating
rmdir /s /q "%BACKEND%\.venv" 2>nul
:createvenv
echo  Creating .venv with %PY_CMD% ...
%PY_CMD% -m venv "%BACKEND%\.venv"
if errorlevel 1 (
    echo  [FAILED] Could not create .venv
    exit /b 1
)
echo  [OK] .venv created
exit /b 0

:step2
if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo  [FAILED] .venv missing - run step 1 first
    exit /b 1
)
echo  Running pip install - this can take a few minutes ...
cd /d "%BACKEND%"
"%BACKEND%\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [FAILED] pip install
    exit /b 1
)
echo  [OK] Python dependencies installed
exit /b 0

:step3
if not defined FLUTTER_CMD (
    echo  [FAILED] Flutter SDK not found - set FLUTTER_ROOT or add flutter to PATH
    exit /b 1
)
echo  Running flutter pub get - this can take a few minutes ...
cd /d "%FRONTEND%"
call "%FLUTTER_CMD%" pub get
if errorlevel 1 (
    echo  [FAILED] flutter pub get
    exit /b 1
)
echo  [OK] Flutter packages fetched
exit /b 0

:step4
if not defined FLUTTER_CMD (
    echo  [FAILED] Flutter SDK not found - set FLUTTER_ROOT or add flutter to PATH
    exit /b 1
)
echo  Running flutter build web - this can take a few minutes ...
cd /d "%FRONTEND%"
call "%FLUTTER_CMD%" build web
if errorlevel 1 (
    echo  [FAILED] flutter build web
    exit /b 1
)
echo  [OK] Web build written to %FRONTEND%\build\web
exit /b 0

:quit
echo.
echo  Aborted by user.

:finish
echo ============================================================
if "%FAILED%"=="1" (
    echo  SETUP FINISHED WITH ERRORS
) else (
    echo  SETUP COMPLETE
)
echo  Backend venv : %BACKEND%\.venv
echo  Web build    : %FRONTEND%\build\web
echo  Start app    : Scripts\start.bat
echo ============================================================
echo  Closing in 8 seconds ...
timeout /t 8 >nul
exit /b 0

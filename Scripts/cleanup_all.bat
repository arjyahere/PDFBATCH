@echo off
setlocal EnableDelayedExpansion
title Cleanup All - keep input/ and output/

cd /d "%~dp0.."
set "ROOT=%CD%"
set "BACKEND=%ROOT%\batch_highlighter_api_integrated"
set "FRONTEND=%ROOT%\flutter_frontend"
set "REMOVED=0"

cls
echo ============================================================
echo                      CLEANUP ALL
echo ============================================================
echo  Root: %ROOT%
echo.
echo  Removes generated artifacts:
echo    - Python venvs (.venv / venv)
echo    - __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, *.pyc
echo    - Flutter .dart_tool and build folders
echo    - logs folders and crash logs
echo    - temp, jobs, temp_*, *.db, *.sqlite, *.sqlite3
echo.
echo  PRESERVED: source code, .git, Scripts, Docs, and EVERY
echo             input/ and output/ folder anywhere in the repo.
echo.
choice /c YN /n /t 20 /d N /m "  Delete all generated artifacts? [Y]es / [N]o : "
if errorlevel 2 goto :cancel

echo.
echo [1/6] Virtual environments
for %%V in ("%ROOT%\.venv" "%ROOT%\venv" "%BACKEND%\.venv" "%BACKEND%\venv") do (
    if exist "%%~V" (
        echo   Removing %%~V
        rmdir /s /q "%%~V" 2>nul
        set /a REMOVED+=1
    )
)

echo [2/6] Python / tool caches
for /d /r "%ROOT%" %%D in (__pycache__ .pytest_cache .mypy_cache .ruff_cache) do (
    set "P=%%D"
    set "Q=!P:\input\=!"
    if "!Q!"=="!P!" set "Q=!P:\output\=!"
    if "!Q!"=="!P!" if exist "!P!" (
        echo   Removing !P!
        rmdir /s /q "!P!" 2>nul
        set /a REMOVED+=1
    )
)
for /r "%ROOT%" %%F in (*.pyc *.pyo) do (
    set "P=%%F"
    set "Q=!P:\input\=!"
    if "!Q!"=="!P!" set "Q=!P:\output\=!"
    if "!Q!"=="!P!" if exist "!P!" (
        del /q "!P!" 2>nul
        set /a REMOVED+=1
    )
)

echo [3/6] Flutter build artifacts
for %%D in ("%FRONTEND%\.dart_tool" "%FRONTEND%\build") do (
    if exist "%%~D" (
        echo   Removing %%~D
        rmdir /s /q "%%~D" 2>nul
        set /a REMOVED+=1
    )
)

echo [4/6] Logs
for %%D in ("%ROOT%\logs" "%BACKEND%\logs") do (
    if exist "%%~D" (
        echo   Removing %%~D
        rmdir /s /q "%%~D" 2>nul
        set /a REMOVED+=1
    )
)
for %%F in ("%ROOT%\hs_err_*.log" "%ROOT%\replay_*.log") do (
    if exist "%%~F" (
        echo   Removing %%~nxF
        del /q "%%~F" 2>nul
        set /a REMOVED+=1
    )
)

echo [5/6] Runtime folders (temp / jobs)
for /d /r "%ROOT%" %%D in (temp jobs temp_*) do (
    set "P=%%D"
    set "Q=!P:\input\=!"
    if "!Q!"=="!P!" set "Q=!P:\output\=!"
    if "!Q!"=="!P!" if exist "!P!" (
        echo   Removing !P!
        rmdir /s /q "!P!" 2>nul
        set /a REMOVED+=1
    )
)

echo [6/6] Runtime databases
for /r "%ROOT%" %%F in (*.db *.sqlite *.sqlite3) do (
    set "P=%%F"
    set "Q=!P:\input\=!"
    if "!Q!"=="!P!" set "Q=!P:\output\=!"
    if "!Q!"=="!P!" if exist "!P!" (
        echo   Removing !P!
        del /q "!P!" 2>nul
        set /a REMOVED+=1
    )
)

echo.
echo ============================================================
echo   Removed %REMOVED% folders/files
echo   Preserved: input/, output/, source code, .git
echo ============================================================
echo   Closing in 8 seconds ...
timeout /t 8 >nul
exit /b 0

:cancel
echo   Cancelled - nothing was deleted.
timeout /t 5 >nul
exit /b 0

@echo off
setlocal
cd /d "%~dp0"

set "PROJECT_PYTHON="
for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('where python3 2^>nul') do if not defined PROJECT_PYTHON set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('dir /b /s "%LocalAppData%\Programs\Python\Python3*\python.exe" 2^>nul') do if not defined PROJECT_PYTHON set "PROJECT_PYTHON=%%P"

if not defined PROJECT_PYTHON (
    echo Python 3 was not found. The "python" command on this PC is Python 2.7.
    echo Install Python 3.10 or newer and run this file again.
    pause
    exit /b 1
)

set "PYTHONPATH=%CD%\.packages"
"%PROJECT_PYTHON%" -c "from flask import Flask; from ping3 import ping; from PIL import Image; from reportlab.lib import colors; from reportlab.platypus import SimpleDocTemplate" >nul 2>&1
if errorlevel 1 goto dependencies_missing
goto run_application

:dependencies_missing
echo ERROR: Project dependencies are not installed.
echo First run: install-dependencies.cmd
pause
exit /b 1

:run_application
echo Starting Live IP Monitor...
echo Access information will be displayed below.
echo Keep this window open while users access the dashboard.
echo.
"%PROJECT_PYTHON%" APP.py
if errorlevel 1 (
    echo.
    echo ERROR: Application stopped with an error.
    pause
    exit /b 1
)
pause

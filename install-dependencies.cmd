@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_INSTALL_ATTEMPTED="

:find_python
set "PROJECT_PYTHON="
for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('where python3 2^>nul') do if not defined PROJECT_PYTHON set "PROJECT_PYTHON=%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('dir /b /s "%LocalAppData%\Programs\Python\Python3*\python.exe" 2^>nul') do if not defined PROJECT_PYTHON set "PROJECT_PYTHON=%%P"

if defined PROJECT_PYTHON goto python_ready
if defined PYTHON_INSTALL_ATTEMPTED goto python_not_found

set "PYTHON_INSTALL_ATTEMPTED=1"
where winget >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 and Windows Package Manager winget were not found.
    echo Install Python 3.10 or newer, then run this file again.
    pause
    exit /b 1
)

echo Python 3 was not found.
echo Installing Python 3.13 for the current Windows user...
winget install --id Python.Python.3.13 --exact --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo ERROR: Automatic Python installation failed.
    pause
    exit /b 1
)
goto find_python

:python_not_found
echo ERROR: Python installation completed, but python.exe could not be located.
echo Close this window and run install-dependencies.cmd again.
pause
exit /b 1

:python_ready
echo Using Python:
echo %PROJECT_PYTHON%
echo.
echo Installing dependencies locally in C:\Sev1\.packages...
"%PROJECT_PYTHON%" -m pip install --upgrade --target ".packages" -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo.
set "PYTHONPATH=%CD%\.packages"
"%PROJECT_PYTHON%" -c "from flask import Flask; from ping3 import ping; from PIL import Image; from reportlab.lib import colors; from reportlab.platypus import SimpleDocTemplate" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Packages downloaded, but dependency validation failed.
    pause
    exit /b 1
)

echo Dependencies installed and validated successfully.
echo You can now start the project using run-local.cmd
pause

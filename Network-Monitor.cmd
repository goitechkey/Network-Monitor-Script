@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "TASK_NAME=Live IP Monitor"
set "LOG_FILE=%~dp0monitor-service.log"

if /i "%~1"=="--service" goto service
if /i "%~1"=="--verify" goto verify
if /i "%~1"=="--remove" goto remove_task
if /i "%~1"=="--elevated" goto setup

echo.
echo Dashboard link: http://localhost:5000
echo This link will work after the one-time setup completes.
echo.
echo Requesting administrator permission for one-time setup...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '--elevated' -Verb RunAs"
if errorlevel 1 (
    echo ERROR: Administrator permission was not granted.
    call :wait
)
goto end

:setup
echo.
echo Dashboard link: http://localhost:5000
echo.
call :install_dependencies
if errorlevel 1 goto setup_failed
call :install_task
if errorlevel 1 goto setup_failed
echo.
echo Setup complete. No action is needed after restart.
echo Dashboard: http://localhost:5000
call :wait
goto end

:install_task
call :verify_dependencies
if errorlevel 1 (
    echo.
    echo ERROR: Project dependencies are not installed.
    exit /b 1
)

set "TASK_COMMAND=\"%SystemRoot%\System32\wscript.exe\" //B \"\"%~dp0Network-Monitor-Background.vbs\"\""
echo.
echo Registering automatic startup task...
schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /IT /TR "%TASK_COMMAND%" /F
if errorlevel 1 (
    echo.
    echo ERROR: The task could not be created or updated.
    echo Right-click this file and choose Run as administrator, then run it once more.
    exit /b 1
)

schtasks /Run /TN "%TASK_NAME%" >nul 2>&1
echo Automatic startup enabled.
exit /b 0

:remove_task
echo.
echo Removing automatic startup task...
schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
    echo.
    echo ERROR: The task could not be removed.
    echo Right-click this file and choose Run as administrator, then run:
    echo Network-Monitor.cmd --remove
) else (
    echo Automatic startup removed.
)
call :wait
goto end

:service
call :verify_dependencies >nul 2>&1
if errorlevel 1 (
    >> "%LOG_FILE%" echo [%date% %time%] ERROR: Python or project dependencies are unavailable.
    exit /b 1
)

>> "%LOG_FILE%" echo [%date% %time%] Live IP Monitor started.
"%PROJECT_PYTHON%" APP.py >> "%LOG_FILE%" 2>&1
>> "%LOG_FILE%" echo [%date% %time%] Live IP Monitor stopped with exit code %errorlevel%.
exit /b

:verify
call :verify_dependencies
if errorlevel 1 exit /b 1
echo Python and project dependencies are ready.
exit /b 0

:install_dependencies
call :verify_dependencies
if not errorlevel 1 (
    > ".monitor-python-path" echo %PROJECT_PYTHON%
    exit /b 0
)
call :find_python
if not defined PROJECT_PYTHON (
    where winget >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python 3 was not found and winget is unavailable.
        echo Install Python 3.10 or newer, then run this file again.
        exit /b 1
    )
    echo Python 3 was not found. Installing Python 3.13 for the current user...
    winget install --id Python.Python.3.13 --exact --scope user --accept-package-agreements --accept-source-agreements
    if errorlevel 1 exit /b 1
    call :find_python
)

if not defined PROJECT_PYTHON (
    echo ERROR: Python installation completed, but a usable python.exe was not found.
    exit /b 1
)

echo Using Python:
echo %PROJECT_PYTHON%
echo.
echo Installing project dependencies...
"%PROJECT_PYTHON%" -m pip install --upgrade -r requirements.txt
if errorlevel 1 exit /b 1
call :verify_dependencies
if not errorlevel 1 > ".monitor-python-path" echo %PROJECT_PYTHON%
exit /b %errorlevel%

:verify_dependencies
set "PROJECT_PYTHON="
if exist ".monitor-python-path" set /p PROJECT_PYTHON=<".monitor-python-path"
if defined PROJECT_PYTHON if not exist "%PROJECT_PYTHON%" set "PROJECT_PYTHON="
if not defined PROJECT_PYTHON call :find_python
if not defined PROJECT_PYTHON exit /b 1
set "PYTHONPATH="
"%PROJECT_PYTHON%" -c "from flask import Flask; from ping3 import ping; from PIL import Image; from reportlab.lib import colors; from reportlab.platypus import SimpleDocTemplate" >nul 2>&1
exit /b %errorlevel%

:find_python
set "PROJECT_PYTHON="
for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do call :use_python "%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do call :use_python "%%P"
if not defined PROJECT_PYTHON for /f "delims=" %%P in ('dir /b /s "%LocalAppData%\Programs\Python\python.exe" 2^>nul') do call :use_python "%%P"
if not defined PROJECT_PYTHON for /d %%D in ("%ProgramFiles%\Python3*") do call :use_python "%%~fD\python.exe"
if not defined PROJECT_PYTHON for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :use_python "%%~fD\python.exe"
exit /b 0

:use_python
if defined PROJECT_PYTHON exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys" >nul 2>&1
if not errorlevel 1 set "PROJECT_PYTHON=%~1"
exit /b 0

:wait
echo.
pause
exit /b 0

:setup_failed
echo.
echo Setup could not be completed. Read the error above, then run this file again.
call :wait
goto end

:end
endlocal
exit /b 0

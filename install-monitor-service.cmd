@echo off
setlocal
cd /d "%~dp0"

set "TASK_NAME=Live IP Monitor"
set "START_SCRIPT=%~dp0run-local.cmd"

echo Registering "%TASK_NAME%" to start automatically at Windows logon...
schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "\"%ComSpec%\" /c \"\"%START_SCRIPT%\"\"" /F
if errorlevel 1 (
    echo.
    echo ERROR: Could not register the startup task.
    echo Try running this file as Administrator.
    pause
    exit /b 1
)

echo.
echo Live IP Monitor has been registered successfully.
echo It will start automatically after the next Windows logon.
echo Starting it now...
schtasks /Run /TN "%TASK_NAME%" >nul
echo.
echo To remove automatic startup, run uninstall-monitor-service.cmd
pause

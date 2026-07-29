@echo off
setlocal
set "TASK_NAME=Live IP Monitor"

schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
    echo Task was not found or could not be removed.
    pause
    exit /b 1
)

echo Automatic startup removed successfully.
pause

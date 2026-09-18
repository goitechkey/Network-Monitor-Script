@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "APP_PATH=%CD%\APP.py"
set "BACKGROUND_LAUNCHER=%CD%\Network-Monitor-Background.vbs"

if not exist "%APP_PATH%" (
    echo ERROR: APP.py was not found in this folder.
    goto :done
)

if not exist "%BACKGROUND_LAUNCHER%" (
    echo ERROR: Network-Monitor-Background.vbs was not found in this folder.
    goto :done
)

echo.
echo Stopping the current Network Monitor...
set "STOP_FAILED="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5000 .*LISTENING"') do (
    echo Stopping process %%P using the monitor port...
    taskkill /F /PID %%P >nul 2>&1
    if errorlevel 1 set "STOP_FAILED=1"
)

if defined STOP_FAILED (
    echo ERROR: The current monitor could not be stopped.
    goto :done
)

timeout /t 2 /nobreak >nul

echo Starting the Network Monitor in the background...
start "" /b wscript.exe "%BACKGROUND_LAUNCHER%"
if errorlevel 1 (
    echo ERROR: The monitor could not be started.
    goto :done
)

timeout /t 3 /nobreak >nul

netstat -ano | findstr /R /C:":5000 .*LISTENING" >nul
if errorlevel 1 (
    echo ERROR: The monitor started but is not listening on port 5000.
) else (
    echo Network Monitor restarted successfully.
    echo Dashboard: http://localhost:5000
)

:done
echo.
pause
endlocal

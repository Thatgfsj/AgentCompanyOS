@echo off
REM BUG-FRONTEND-RT-13: the Flowntier sidecar binary
REM (flowntier_runtime.exe) was leaking between installs.
REM Kill BOTH the main app and the sidecar so the install
REM can overwrite both. Run as Administrator if you installed
REM to Program Files (we install to currentUser so admin
REM shouldn't be needed for the standard install path).

echo Checking for running Flowntier processes...

REM Main app
tasklist /FI "IMAGENAME eq flowntier.exe" 2>NUL | find /I /N "flowntier.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo Found Flowntier main process. Terminating...
    taskkill /F /IM flowntier.exe
)

REM Sidecar binary (Python runtime bridge)
tasklist /FI "IMAGENAME eq flowntier_runtime.exe" 2>NUL | find /I /N "flowntier_runtime.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo Found Flowntier sidecar process. Terminating...
    taskkill /F /IM flowntier_runtime.exe
)

REM Also kill any pipe-server lingering process
tasklist /FI "IMAGENAME eq pipe-server.exe" 2>NUL | find /I /N "pipe-server.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo Found pipe-server process. Terminating...
    taskkill /F /IM pipe-server.exe
)

REM Give the OS a moment to release file handles
timeout /T 2 /NOBREAK >NUL

echo.
echo All Flowntier processes terminated. You can now run the installer.
pause
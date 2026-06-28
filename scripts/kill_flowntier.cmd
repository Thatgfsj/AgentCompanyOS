@echo off
REM BUG-FRONTEND-RT-11: the Flowntier NSIS installer cannot
REM overwrite flowntier_runtime.exe while a previous Flowntier
REM instance is running. This script terminates any running
REM Flowntier process so the install can proceed. Run as
REM Administrator if you installed to Program Files (we install
REM to currentUser so admin shouldn't be needed).

echo Checking for running Flowntier process...

tasklist /FI "IMAGENAME eq flowntier.exe" 2>NUL | find /I /N "flowntier.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo Found Flowntier running. Terminating...
    taskkill /F /IM flowntier.exe
    if "%ERRORLEVEL%"=="0" (
        echo Flowntier process terminated.
    ) else (
        echo ERROR: Failed to terminate Flowntier.
        echo Try running this script as Administrator.
        exit /B 1
    )
) else (
    echo No Flowntier process running.
)

REM Give the OS a moment to release file handles
timeout /T 1 /NOBREAK >NUL

echo.
echo You can now run the Flowntier installer.
pause
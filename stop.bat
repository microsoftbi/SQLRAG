@echo off
echo Stopping SQLRAG System...

echo.
echo Killing backend processes...
taskkill /FI "WINDOWTITLE eq SQLRAG Backend*" /T /F >nul 2>&1

echo.
echo Killing frontend processes...
taskkill /FI "WINDOWTITLE eq SQLRAG Frontend*" /T /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

echo.
echo SQLRAG System stopped.
pause

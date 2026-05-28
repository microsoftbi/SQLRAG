@echo off
echo Starting SQLRAG System...

echo.
echo [1/2] Starting Backend on port 8798...
start "SQLRAG Backend" cmd /k "cd backend && pip install -r requirements.txt && python main.py"

timeout /t 5 /nobreak >nul

echo.
echo [2/2] Starting Frontend on port 3300...
start "SQLRAG Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo SQLRAG System is starting!
echo Backend: http://localhost:8798
echo Frontend: http://localhost:3300
echo.
pause

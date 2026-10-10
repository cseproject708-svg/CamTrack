@echo off
REM Campus Gate Access Control - one-click starter (Backend :8000 + Frontend :3000)
cd /d "%~dp0"

echo ============================================
echo  Campus Gate Access Control - Starting...
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.11 first.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found in PATH. Install Node.js 18+ first.
    pause
    exit /b 1
)

echo [1/4] Initializing database...
python -m server.database
if errorlevel 1 (
    echo [WARN] Database init reported an error - continuing anyway.
)

if not exist "frontend\node_modules" (
    echo [2/4] Installing frontend dependencies (first run only)...
    cd frontend
    call npm install
    cd /d "%~dp0"
) else (
    echo [2/4] Frontend dependencies found, skipping npm install.
)

echo [3/4] Starting backend on http://localhost:8000 ...
start "CampusGate-Backend" cmd /k python -m server.main

echo [4/4] Starting frontend on http://localhost:3000 ...
start "CampusGate-Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo Waiting for servers to come up...
timeout /t 10 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo ============================================
echo  Backend:  http://localhost:8000/api/health
echo  Frontend: http://localhost:3000
echo  Close the two popup windows to stop.
echo ============================================
pause

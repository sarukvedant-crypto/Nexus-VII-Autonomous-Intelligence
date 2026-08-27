@echo off
title J.A.R.V.I.S. HUD
echo.
echo ============================================
echo   J.A.R.V.I.S. HUD - Starting Server...
echo ============================================
echo.

cd /d "%~dp0"

:: Kill any stuck background processes on port 8000 to prevent crashing
FOR /F "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%a >nul 2>&1

:: Wait a moment then open browser
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Start the server (this keeps the window alive)
echo [OK] Server starting at http://localhost:8000
echo [OK] Close this window to shut down J.A.R.V.I.S.
echo.
venv\Scripts\python core\server.py

echo.
echo [!] J.A.R.V.I.S. Server stopped unexpectedly!
pause

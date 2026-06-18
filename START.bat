@echo off
REM ============================================================
REM  NIFTY AI BOT — One-click launcher (Windows)
REM  Double-click this file to start everything.
REM ============================================================

echo.
echo  ============================================
echo   NIFTY AI BOT - Starting...
echo  ============================================
echo.

cd backend

REM Create venv if it doesn't exist
if not exist venv (
    echo  First run - creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo  Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo  ============================================
echo   Server starting at http://localhost:8000
echo   Opening browser...
echo  ============================================
echo.

REM Open browser after a short delay
start "" cmd /c "timeout /t 4 >nul && start http://localhost:8000"

REM Run the all-in-one server (backend + serves frontend)
python main.py

pause

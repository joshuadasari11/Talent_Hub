@echo off
echo.
echo  =========================================
echo   TalentHub - Campus Placement Portal
echo  =========================================
echo.
echo  Starting server at http://127.0.0.1:5000
echo  Press Ctrl+C to stop
echo.
cd /d "%~dp0"
python app.py
pause

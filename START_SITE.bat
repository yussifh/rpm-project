@echo off
title Start RPM Site
cd /d "%~dp0backend"
start "RPM Backend - keep this window open" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
cd /d "%~dp0frontend"
start "RPM Frontend - keep this window open" cmd /k "node %TEMP%\..\..\Users\YUSSIF\AppData\Local\Temp\opencode\serve-dist.mjs %~dp0frontend\dist 4173 0.0.0.0"
echo.
echo ============================================================
echo  Starting RPM. Your browser should open in a few seconds.
echo  If it does not, go to:  http://localhost:4173
echo  Backend (API):           http://127.0.0.1:8000
echo ============================================================
echo.
echo  Keep the two new black windows open - closing them stops
echo  the site.
echo.
start "" http://localhost:4173
timeout /t 3 >nul
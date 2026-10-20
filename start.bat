@echo off
setlocal
start "BuildWise AI Backend" "%~dp0start-backend.bat"
start "BuildWise AI Frontend" "%~dp0start-frontend.bat"
echo.
echo Wait for both windows to finish installing and starting.
echo Frontend: http://127.0.0.1:5173
echo Backend docs: http://127.0.0.1:8000/docs
echo.
pause

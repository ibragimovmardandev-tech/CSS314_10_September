@echo off
cd /d "%~dp0"
echo Starting Parallel Computing Lab...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0parallel_lab.ps1"
echo.
echo ==========================================
echo Script finished or stopped with an error.
echo Take a screenshot of this window if you see an error.
echo ==========================================
pause

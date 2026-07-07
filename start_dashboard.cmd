@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_dashboard_windows.ps1"
set EXITCODE=%ERRORLEVEL%

if /I "%~1" NEQ "--no-pause" pause
exit /b %EXITCODE%

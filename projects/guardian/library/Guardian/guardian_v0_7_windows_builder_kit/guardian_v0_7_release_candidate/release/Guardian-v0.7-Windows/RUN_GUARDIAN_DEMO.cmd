@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\RUN_GUARDIAN_DEMO.ps1"
exit /b %errorlevel%

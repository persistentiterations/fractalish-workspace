@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\VALIDATE_WINDOWS_RELEASE.ps1"
exit /b %errorlevel%

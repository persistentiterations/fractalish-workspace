@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\CHECK_RELEASE_CHECKSUMS.ps1"
exit /b %errorlevel%

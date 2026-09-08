@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title דחיפה ל-GitHub
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push-to-github.ps1" %*
echo.
pause

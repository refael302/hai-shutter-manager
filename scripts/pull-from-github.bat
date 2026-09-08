@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title משיכה מ-GitHub
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pull-from-github.ps1"
echo.
pause

@echo off
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Apply-Dashboard-Update.ps1"
pause

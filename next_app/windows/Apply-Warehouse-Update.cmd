@echo off
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Apply-Warehouse-Update.ps1"
pause

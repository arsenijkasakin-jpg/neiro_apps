@echo off
setlocal
cd /d "%~dp0"
py assistant.py
if %errorlevel% neq 0 python assistant.py
pause

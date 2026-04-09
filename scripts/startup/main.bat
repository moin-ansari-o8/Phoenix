@echo off
echo Just MainPHNX is starting...

REM Change directory to project folder
cd /d C:\STDY\MYAIS\Phoenix

REM Use virtual environment python directly instead of activating
.venv\Scripts\python.exe main.py

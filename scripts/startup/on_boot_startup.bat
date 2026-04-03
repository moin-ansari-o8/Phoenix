@echo off
echo "phoenix is starting..."
cd /d C:\STDY\MYAIS\Phoenix
REM Use virtual environment python directly instead of activating
start "" /B .venv\Scripts\python.exe load.py
exit
@echo off
echo "phoenix is starting..."
cd /d C:\STDY\GIT_PROJECTS\Phoenix
REM Activate virtual environment
call .venv\Scripts\activate

start "" /B python load.py
exit
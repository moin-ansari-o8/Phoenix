@echo off
echo Just MainPHNX is starting...

REM Change directory to project folder
cd /d C:\STDY\GIT_PROJECTS\Phoenix

REM Activate virtual environment
call .venv\Scripts\activate

REM Run the main Python file
python MainPHNX.py

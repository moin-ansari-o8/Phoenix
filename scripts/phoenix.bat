@echo off
REM Check if the first argument is "start"
if "%1" == "start" (
    echo "phoenix is starting..."
    cd /d C:\STDY\GIT_PROJECTS\Phoenix
    REM Activate virtual environment
    call .venv\Scripts\activate

    start "" /B python load.py
    exit
) else if "%1" == "main" (
    echo "just MainPHNX is starting..."
    
    cd C:\STDY\GIT_PROJECTS\Phoenix
    REM Activate virtual environment
    call .venv\Scripts\activate

    python MainPHNX.py
) else (
    echo Invalid command. Use "phoenix start/main" to run the program.
)

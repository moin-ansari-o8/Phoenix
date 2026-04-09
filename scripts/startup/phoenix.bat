@echo off
REM Check if the first argument is "start"
if "%1" == "start" (
    echo "phoenix is starting..."
    cd /d C:\STDY\MYAIS\Phoenix
    REM Activate virtual environment
    call .venv\Scripts\activate

    start "" /B python load.py
    exit
) else if "%1" == "main" (
    echo "just MainPHNX is starting..."
    
    cd /d C:\STDY\MYAIS\Phoenix

    REM Use virtual environment python directly instead of activating
    .venv\Scripts\python.exe main.py
) else (
    echo Invalid command. Use "phoenix start/main" to run the program.
)

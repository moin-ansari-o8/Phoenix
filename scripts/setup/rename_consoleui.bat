@echo off
REM Rename ConsoleUI_new.py to ConsoleUI.py

echo Renaming ConsoleUI files...
cd helpers
if exist ConsoleUI_new.py (
    if exist ConsoleUI.py (
        del ConsoleUI.py
        echo Deleted old ConsoleUI.py
    )
    ren ConsoleUI_new.py ConsoleUI.py
    echo Renamed ConsoleUI_new.py to ConsoleUI.py
    echo Done!
) else (
    echo ConsoleUI_new.py not found - may have already been renamed
)
cd ..
pause

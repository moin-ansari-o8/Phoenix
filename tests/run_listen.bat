@echo off
REM Run listen.py with absolute paths to avoid venv config issues

echo Starting Phoenix Advanced Listening System...
echo.

REM Use the venv Python with absolute path
C:\STDY\MYAIS\Phoenix\.venv\Scripts\python.exe W:\workplace-1\DeskAssistants\Phoenix\tests\listen.py

pause

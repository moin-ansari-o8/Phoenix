@echo off
REM Simple UV sync for Phoenix

echo Phoenix - UV Sync
echo ==================

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo UV not found!
    echo Install: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo Running uv sync...
uv sync

if %errorlevel% equ 0 (
    echo.
    echo Done! Now run:
    echo   .venv\Scripts\activate.bat
    echo   python main.py
) else (
    echo.
    echo Failed! Close terminal and try again.
)

pause

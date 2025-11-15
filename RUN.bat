@echo off
rem --- Change working directory to this bat file's location ---
cd /d "%~dp0"

rem --- Check if venv python exists ---
if not exist "venv\Scripts\python.exe" (
    echo [!] Virtual environment not found in '.\venv'.
    echo [!] Please run 'setup.bat' first to install dependencies.
    pause
    exit /b
)

echo [*] Starting Soundboard using Virtual Environment...

rem --- Run the main script using venv's python ---
"venv\Scripts\python.exe" "soundboard.py"
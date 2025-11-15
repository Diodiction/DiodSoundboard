@echo off
rem --- Change working directory to this bat file's location ---
cd /d "%~dp0"

echo [*] Finding Python and running setup script...
echo [*] This will create a 'venv' folder and install libraries.
echo [*] It will also create 'Soundboard Rsc' with an example file.
echo.

rem --- Run the setup script using system's python ---
python setup_soundboard.py

echo.
echo [*] Setup complete. 
echo [*] You can now run 'run_soundboard.bat' to start the program.

rem --- Pause to check for errors ---
pause
@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 pause & exit /b 1
py -m PyInstaller --onefile --windowed --name RLBoostHUD rl_boost_hud.py
if errorlevel 1 pause & exit /b 1
echo Your executable is in dist\RLBoostHUD.exe
pause

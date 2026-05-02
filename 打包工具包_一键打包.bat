@echo off
cd /d "%~dp0"
echo ================================================
echo   Video Downloader v3.0 - Build EXE
echo   Author: MingChen  Vx: MingCv1
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller ...
pip install pyinstaller --quiet

echo [2/3] Building EXE with icon ...
echo.
python -m PyInstaller --onefile --windowed --name "VideoDownloader" --icon=icon.ico video_downloader.py

if errorlevel 1 (
    echo.
    echo [FAIL] Build failed
    pause
    exit /b 1
)

echo [3/3] Cleaning temp files ...
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist VideoDownloader.spec del /q VideoDownloader.spec

echo.
echo ================================================
echo              Build Complete!
echo ================================================
echo.
echo EXE: dist\VideoDownloader.exe
echo Note: install ffmpeg for audio feature
echo       Run: winget install ffmpeg
echo.
pause

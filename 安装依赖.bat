@echo off
cd /d "%~dp0"
echo ========================================
echo   Video Downloader - Install Deps
echo   Author: MingChen  Vx: MingCv1
echo ========================================
echo.

echo [1/3] Installing yt-dlp ...
pip install yt-dlp --quiet
if %errorlevel% neq 0 (
    echo [FAIL] yt-dlp install failed
    pause
    exit /b 1
)
echo [OK] yt-dlp

echo.
echo [2/3] Installing requests ...
pip install requests --quiet
if %errorlevel% neq 0 (
    echo [FAIL] requests install failed
    pause
    exit /b 1
)
echo [OK] requests

echo.
echo [3/3] Installing pyperclip ...
pip install pyperclip --quiet
if %errorlevel% neq 0 (
    echo [FAIL] pyperclip install failed
    pause
    exit /b 1
)
echo [OK] pyperclip

echo.
echo ========================================
echo   Checking ffmpeg ...
echo ========================================
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] ffmpeg not found, installing ...
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo [FAIL] ffmpeg install failed, run manually:
        echo    winget install ffmpeg
    ) else (
        echo [OK] ffmpeg installed, restart PowerShell
    )
) else (
    echo [OK] ffmpeg already installed
)

echo.
echo ========================================
echo   All done! Run video_downloader.py
echo ========================================
echo.
pause

@echo off
cd /d "%~dp0"

echo ================================================
echo   Video Downloader v3.0 - Installer
echo   Author: MingChen  Vx: MingCv1
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not installed!
    echo Please install from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python found
python --version

echo.
echo [1/6] Creating folder...
set "TARGET=%USERPROFILE%\Desktop\VideoDownloader"
if not exist "%TARGET%" mkdir "%TARGET%"
if not exist "%TARGET%\downloads" mkdir "%TARGET%\downloads"
if not exist "%TARGET%\downloads\video" mkdir "%TARGET%\downloads\video"
if not exist "%TARGET%\downloads\audio" mkdir "%TARGET%\downloads\audio"
echo [OK] Folder: %TARGET%

echo.
echo [2/6] Writing program file...
if not exist "%~dp0vd.b64" (
    echo [ERROR] vd.b64 not found! Put it next to this bat file.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b = [IO.File]::ReadAllText('%~dp0vd.b64'); $d = [Convert]::FromBase64String($b); $s = [Text.Encoding]::UTF8.GetString($d); [IO.File]::WriteAllText('%TARGET%\video_downloader.py', $s)"
if not exist "%TARGET%\video_downloader.py" (
    echo [ERROR] Failed to write program file
    pause
    exit /b 1
)
echo [OK] video_downloader.py

echo.
echo [3/6] Installing yt-dlp...
pip install yt-dlp --quiet
echo [OK] yt-dlp

echo.
echo [4/6] Installing requests...
pip install requests --quiet
echo [OK] requests

echo.
echo [5/6] Installing pyperclip...
pip install pyperclip --quiet
echo [OK] pyperclip

echo.
echo [6/6] Checking ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo ffmpeg not found, installing...
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [WARN] ffmpeg install failed, run manually: winget install ffmpeg
    ) else (
        echo [OK] ffmpeg installed, restart PowerShell to take effect
    )
) else (
    echo [OK] ffmpeg already installed
)

echo.
echo Creating shortcut and launcher...

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\VideoDownloader.lnk'); $sc.TargetPath = 'pythonw'; $sc.Arguments = '%TARGET%\video_downloader.py'; $sc.WorkingDirectory = '%TARGET%'; $sc.Save()"

echo @echo off > "%TARGET%\Start.bat"
echo cd /d "%TARGET%" >> "%TARGET%\Start.bat"
echo python video_downloader.py >> "%TARGET%\Start.bat"
echo pause >> "%TARGET%\Start.bat"

echo.
echo ================================================
echo   Install Complete!
echo ================================================
echo.
echo   Folder: %TARGET%
echo   Shortcut: Desktop - VideoDownloader
echo   Or run: %TARGET%\Start.bat
echo.
echo   Note: ffmpeg needed for audio extraction
echo         Run: winget install ffmpeg
echo.
pause

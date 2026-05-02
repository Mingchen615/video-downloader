@echo off
REM 短视频下载器 v4.0 快速启动
REM 自动安装依赖并启动程序

cd /d "%~dp0"

echo ========================================
echo   短视频下载器 v4.0
echo   音频转文字版
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    echo 请先从 Microsoft Store 安装 Python 3.9+
    pause
    exit /b 1
)

echo [检查] Python 版本 OK
echo.

REM 检查并安装依赖
echo [检查] 安装必要依赖...

pip show yt-dlp >nul 2>&1
if errorlevel 1 (
    echo [安装] yt-dlp...
    pip install yt-dlp -q
)

pip show requests >nul 2>&1
if errorlevel 1 (
    echo [安装] requests...
    pip install requests -q
)

pip show pyperclip >nul 2>&1
if errorlevel 1 (
    echo [安装] pyperclip...
    pip install pyperclip -q
)

pip show faster-whisper >nul 2>&1
if errorlevel 1 (
    echo [安装] faster-whisper（首次安装较慢）...
    echo [提示] 如果安装失败，请参考 安装说明.md
    pip install faster-whisper -q
)

echo [完成] 依赖检查完成
echo.

REM 检查ffmpeg
echo [检查] ffmpeg 状态...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未检测到 ffmpeg！
    echo [提示] 请运行: winget install ffmpeg
    echo.
)

echo ========================================
echo   正在启动程序...
echo ========================================
echo.

REM 启动程序
python video_downloader.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

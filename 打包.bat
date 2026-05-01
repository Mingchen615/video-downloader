@echo off
REM 短视频下载器 v4.0 打包脚本
REM 使用前请确保已安装所有依赖

cd /d "%~dp0"

echo ========================================
echo   短视频下载器 v4.0 打包工具
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 检查依赖
echo [1/3] 检查依赖...
pip show yt-dlp >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装基础依赖...
    pip install yt-dlp requests pyperclip
)

pip show faster-whisper >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装ASR依赖（首次安装较慢）...
    pip install faster-whisper
)

echo [完成] 依赖检查完成
echo.

REM 创建规格文件
echo [2/3] 创建打包规格...
(
echo # -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['video_downloader.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['yt_dlp', 'pyperclip', 'faster_whisper', 'ctranslate2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='短视频下载器_v4.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='短视频下载器_v4.0',
)
) > video_downloader.spec

echo [完成] 规格文件已创建
echo.

REM 执行打包
echo [3/3] 开始打包（首次较慢，请耐心等待）...
echo.

python -m PyInstaller video_downloader.spec --clean

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    echo 请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 输出目录: dist\短视频下载器_v4.0\
echo 主程序: dist\短视频下载器_v4.0\短视频下载器_v4.0.exe
echo.
echo [提示] 首次运行会自动下载ASR模型
echo.
pause

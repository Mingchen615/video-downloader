# 短视频无水印下载器 v3.0

**作者：铭晨 Vx：MingCv1**

剪贴板监控版 - 复制链接自动下载视频+音频

## 功能

- 📋 剪贴板自动监控，复制即下载
- 🎬 同时下载视频 + 提取音频MP3
- 🚫 无水印下载
- 支持平台：抖音、B站、小红书、快手
- 视频保存在 `downloads/video/`，音频保存在 `downloads/audio/`

## 快速开始

### 一键安装

1. 下载 `安装包.bat` 和 `vd.b64`（放在同一文件夹）
2. 双击 `安装包.bat`
3. 桌面生成快捷方式，双击使用

### 手动安装

```bash
pip install yt-dlp requests pyperclip
winget install ffmpeg
python video_downloader.py
```

## 打包成EXE

将 `video_downloader.py`、`icon.ico`、`一键打包.bat` 放同一文件夹，双击一键打包.bat。

## 使用方法

1. 启动程序，显示监控中状态
2. 正常浏览视频，复制分享链接
3. 程序自动检测并下载视频+音频

详细说明见 [Windows使用指南.md](Windows使用指南.md)

## 依赖

| 依赖 | 用途 |
|------|------|
| yt-dlp | B站/小红书/快手下载 |
| requests | 抖音API下载 |
| pyperclip | 剪贴板监控 |
| ffmpeg | 音频提取MP3 |

# 短视频无水印下载器 v3.0 使用指南

**作者：铭晨 Vx：MingCv1**

---

## 功能介绍

- 剪贴板自动监控，复制链接即下载
- 同时下载视频 + 提取音频MP3
- 支持平台：抖音、B站、小红书、快手
- 视频保存在 `downloads/video/`，音频保存在 `downloads/audio/`

---

## 安装方式

### 方式一：一键安装包（推荐）

1. 将 `安装包.bat` 和 `vd.b64` 放在同一文件夹
2. 双击 `安装包.bat`
3. 等待自动安装完成
4. 桌面会出现 `VideoDownloader` 快捷方式，双击即可使用

### 方式二：手动安装

1. 安装 Python（3.9+），下载地址：https://www.python.org/downloads/
   - 安装时务必勾选 **"Add Python to PATH"**
2. 安装依赖：
   ```
   pip install yt-dlp requests pyperclip
   ```
3. 安装 ffmpeg（音频提取需要）：
   ```
   winget install ffmpeg
   ```
   装完重启 PowerShell
4. 双击 `video_downloader.py` 运行

### 打包成EXE

1. 确保 `video_downloader.py`、`icon.ico`、`一键打包.bat` 在同一文件夹
2. 双击 `一键打包.bat`
3. 打包完成后 EXE 在 `dist\VideoDownloader.exe`

---

## 使用方法

1. 启动程序，界面显示 **监控中** 状态
2. 正常刷手机/电脑，看到想保存的视频，复制分享链接
3. 程序自动检测链接，下载视频+音频
4. 下载完成后日志区会显示保存位置

### 暂停/继续

- 点击 **暂停** 按钮停止监控
- 点击 **继续** 恢复监控

### 打开下载文件夹

- 点击 **Open Video Folder** 打开视频文件夹
- 点击 **Open Audio Folder** 打开音频文件夹

### 防重复

- 同一链接不会重复下载
- 点击 **Clear History** 清空已处理记录

---

## 文件结构

```
VideoDownloader/
├── video_downloader.py    # 主程序
├── icon.ico               # 程序图标
├── 一键打包.bat            # 打包EXE工具
├── 安装包.bat              # 一键安装
├── vd.b64                 # 程序编码包
├── 安装依赖.bat            # 安装Python依赖
├── Start.bat              # 启动脚本
└── downloads/
    ├── video/             # 下载的视频
    └── audio/             # 提取的音频MP3
```

---

## 常见问题

### Q: 抖音下载失败？
抖音使用第三方API下载，偶尔可能不稳定，稍后重试即可。不需要手动配置cookies。

### Q: B站下载报错？
确保 yt-dlp 是最新版：
```
pip install --upgrade yt-dlp
```

### Q: 音频提取失败？
需要安装 ffmpeg：
```
winget install ffmpeg
```
安装后重启 PowerShell 再运行程序。

### Q: 剪贴板监控不生效？
确保安装了 pyperclip：
```
pip install pyperclip
```

### Q: 双击bat文件闪退/乱码？
bat文件请放在英文路径下运行，避免中文路径问题。

### Q: 打包后EXE图标没变？
Windows有图标缓存，尝试重启资源管理器：
- 任务管理器 → Windows 资源管理器 → 右键重新启动

---

## 依赖清单

| 依赖 | 用途 | 安装命令 |
|------|------|----------|
| yt-dlp | B站/小红书/快手下载 | pip install yt-dlp |
| requests | 抖音API下载 | pip install requests |
| pyperclip | 剪贴板监控 | pip install pyperclip |
| ffmpeg | 音频提取MP3 | winget install ffmpeg |
| PyInstaller | 打包成EXE | pip install pyinstaller |

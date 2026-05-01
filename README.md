# 短视频无水印下载器

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-ff69b4.svg)

一个功能强大的**短视频无水印下载器**，支持抖音、B站、小红书、快手等主流平台。采用剪贴板监控模式，复制链接即可自动下载。同时配备 **ASR 语音转文字**功能，使用 faster-whisper 引擎支持 GPU 加速。

---

## 📌 当前版本：v4.1

### v4.1 更新说明

| 更新内容 | 说明 |
|---------|------|
| 🌐 HuggingFace 国内镜像 | 新增 hf-mirror.com 镜像源，解决模型下载超时问题 |
| 🎵 链接ASR音频优化 | 链接转文字时只下载音频流，不再下载完整视频 |
| 🧹 临时文件自动清理 | ASR识别完成后自动删除临时音频文件 |

---

## ✨ 核心功能

### 🎬 无水印视频下载
- **支持平台**：抖音、B站、小红书、快手
- **剪贴板监控**：复制链接自动检测并下载，无需手动操作
- **自动分类**：按平台自动创建文件夹整理下载文件

### 🎵 音频提取 (MP3)
- 一键提取视频中的音频
- 保存为 MP3 格式
- 无需 Cookies 即可提取

### 📝 ASR 语音转文字
- 使用 **faster-whisper** 语音识别引擎
- **GPU 加速**：支持 NVIDIA CUDA 加速，识别速度提升 4 倍
- **双格式输出**：文字稿(.txt) + 字幕(.srt)
- **多模型选择**：tiny / base / small / medium

### 📊 模型推荐

| 模型 | 显存需求 | 推荐场景 |
|------|---------|---------|
| small | ~2GB | **推荐首选**，速度快，中文效果好 |
| medium | ~5GB | 高精度，适合对准确率要求高的场景 |

---

## 🛠️ 技术栈

| 技术 | 说明 |
|------|------|
| Python 3.10+ | 编程语言 |
| tkinter | GUI 图形界面 |
| yt-dlp | 视频下载核心引擎 |
| faster-whisper | ASR 语音识别（CTranslate2 优化） |
| CUDA | GPU 加速支持 |

---

## 📥 安装说明

### 1. 环境要求

- **Python 3.10+**
- **ffmpeg**（音视频处理必需）
- **NVIDIA CUDA**（GPU 加速可选，推荐）

### 2. 安装步骤

#### 安装 Python 依赖

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install yt-dlp requests pyperclip faster-whisper
```

#### 安装 ffmpeg（必须）

**Windows（winget 推荐）：**
```bash
winget install ffmpeg
```

**Windows（Chocolatey）：**
```bash
choco install ffmpeg
```

**Windows（手动安装）：**
1. 访问 https://ffmpeg.org/download.html
2. 下载 Windows 构建版本
3. 解压到任意目录（如 `C:\ffmpeg`）
4. 将 bin 目录添加到系统 PATH

**macOS：**
```bash
brew install ffmpeg
```

**Linux：**
```bash
sudo apt install ffmpeg
```

#### 验证安装

```bash
ffmpeg -version
python video_downloader.py
```

---

## 📋 依赖列表

```
yt-dlp>=2024.0.0      # 视频下载引擎
requests>=2.28.0      # HTTP 请求库
pyperclip>=1.8.0      # 剪贴板监控
faster-whisper>=1.2.0 # ASR 语音识别
```

---

## 🚀 使用方法

### 启动程序

```bash
python video_downloader.py
```

### 界面说明

程序包含两个主要标签页：

1. **视频下载** - 剪贴板监控模式
   - 启动后自动监控剪贴板
   - 检测到支持的链接后自动下载
   - 视频和音频分别保存

2. **音频转文字** - ASR 功能
   - 可上传本地音频文件
   - 也可直接输入视频链接
   - 选择识别模型（推荐 small）
   - 点击开始识别，自动输出 txt 和 srt 文件

### 支持的链接格式

| 平台 | 示例链接 |
|------|---------|
| 抖音 | `https://v.douyin.com/xxxxx` |
| B站 | `https://www.bilibili.com/video/BVxxxxx` |
| 小红书 | `https://www.xiaohongshu.com/explore/xxxxx` |
| 快手 | `https://v.kuaishou.com/xxxxx` |

---

## 📁 项目结构

```
video-downloader/
├── video_downloader.py    # 主程序
├── requirements.txt       # Python 依赖
├── 安装说明.md             # 安装指南
├── 更新日志.md             # 版本更新记录
├── icon.ico                # 程序图标
├── 启动.bat                # Windows 快速启动
└── 安装依赖.bat            # Windows 一键安装依赖
```

---

## ⚠️ 常见问题

### Q: 下载失败怎么办？
- 检查网络连接
- 确保 ffmpeg 已正确安装
- 抖音视频可能需要更新 Cookies

### Q: ASR 模型下载超时？
- v4.1 已添加 HuggingFace 国内镜像
- 如仍有问题，检查网络代理设置

### Q: GPU 加速不生效？
- 确保已安装 NVIDIA CUDA 12.x
- 确保 cuDNN 已正确配置
- 检查 `nvidia-smi` 是否能识别显卡

---

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业目的。

---

## 📧 反馈与支持

如有问题或建议，请提交 Issue。

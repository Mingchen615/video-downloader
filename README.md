# 短视频无水印下载器

一款支持抖音、B站、小红书、快手等主流平台的无水印视频下载工具，同时具备音频提取和语音转文字(ASR)功能。

## ✨ 核心功能

- 🎬 **无水印下载** - 支持抖音/B站/小红书/快手等平台
- 🎵 **音频提取** - 一键提取MP3格式音频
- 📝 **语音转文字(ASR)** - faster-whisper语音识别，输出txt+srt双格式
- 🔗 **剪贴板监控** - 复制链接自动下载，无需手动操作
- ⚡ **GPU加速** - 支持CUDA加速识别
- 📦 **多模型选择** - tiny/base/small/medium按需选择

## 🚀 快速开始

### 环境要求
- Python 3.10+
- ffmpeg（音视频处理必需）
- NVIDIA CUDA（GPU加速可选）

### 安装步骤

1. **安装Python依赖**
```bash
pip install yt-dlp requests pyperclip faster-whisper
```

2. **安装ffmpeg**
```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

3. **运行程序**
```bash
python video_downloader.py
```

## 📖 使用方法

### 视频下载
1. 复制视频链接
2. 程序自动检测并下载
3. 下载完成后自动保存到 `downloads` 目录

### 音频提取
1. 复制视频链接
2. 点击"提取音频"按钮
3. 自动提取MP3格式音频

### 语音转文字 (ASR)
1. 选择"音频转文字"标签页
2. 上传音频文件或输入视频链接
3. 选择识别模型
4. 点击"开始识别"

### 设备选择
程序支持三种运行设备模式：
- **Auto** - 自动检测GPU可用性，优先使用GPU
- **GPU** - 强制使用GPU加速（需NVIDIA CUDA）
- **CPU** - 使用CPU运行（兼容性更好）

## 🤖 Whisper模型选择

| 模型 | 大小 | 显存 | 推荐度 | 适用场景 |
|------|------|------|--------|----------|
| tiny | 39M | ~1GB | ⭐ 快速测试 | 快速预览 |
| base | 74M | ~1GB | ⭐⭐ 基础识别 | 日常使用 |
| small | 244M | ~2GB | ⭐⭐⭐ **推荐** | 最佳性价比 |
| medium | 769M | ~5GB | ⭐⭐⭐⭐ 高精度 | 专业场景 |

首次使用会自动下载模型（约500MB-3GB）

## 🔧 配置说明

### 抖音Cookies配置（如需下载抖音视频）
1. 登录抖音网页版
2. 使用浏览器扩展（如EditThisCookie）导出Cookies为JSON格式
3. 保存为 `cookies.json` 放在程序同目录

## 📋 更新日志

### v4.3 (2025-05)
- 🔧 **修复链接ASR文字稿保存路径** - 现在自动保存到 `downloads/文字稿/` 文件夹，不再保存到临时目录
- 🎛️ **新增设备选择下拉框** - 支持手动切换运行设备（Auto/GPU/CPU）
- ⚡ **改进CUDA检测逻辑** - 检测顺序优化：nvidia-smi → pip nvidia-cublas → torch.cuda → cublas dll
- 🎯 **GPU模式float32精度** - 避免RTX新架构float16精度问题导致乱码
- 🌍 **HuggingFace镜像提前设置** - 程序启动时即设置镜像，解决模型下载超时
- 🔒 **禁用xet传输协议** - 强制HTTPS走国内镜像
- 📦 **自动配置PATH** - 自动将pip安装的nvidia-cublas DLL目录加入PATH
- 🔍 **实时CUDA检测** - 选GPU时实时检测，不再使用启动缓存值

### v4.2 (2025-01)
- 🔐 **新增抖音Cookies认证** - 解决"Fresh cookies needed"问题

### v4.1 (2025-01)
- 🌍 **HuggingFace国内镜像** - 新增hf-mirror.com镜像源
- 🎵 **链接ASR音频优化** - 只下载音频流，大幅节省时间和存储
- 🧹 **临时文件自动清理** - ASR完成后自动删除临时文件

### v4.0 (2025-01)
- 🎤 **音频转文字功能** - faster-whisper语音识别
- 支持输出txt文字稿和srt字幕双格式

### v3.0 (2024)
- 剪贴板监控模式，复制即下载
- 支持抖音/B站/小红书/快手

## 📦 依赖项

- `yt-dlp` - 视频下载核心
- `faster-whisper` - 语音识别
- `requests` - 网络请求
- `pyperclip` - 剪贴板监控
- `ffmpeg` - 音视频处理

## ⚠️ 注意事项

- 抖音视频下载需要Cookies认证
- faster-whisper需要NVIDIA CUDA支持（可选CPU模式）
- Windows用户需安装Visual Studio Build Tools

## 📄 License

MIT License

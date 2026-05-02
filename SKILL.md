# 短视频下载器 (Short Video Downloader)

## 技能名称
短视频下载器

## 功能描述
> 🔒 **安全版** - 支持抖音、B站、小红书、快手等主流平台的无水印视频下载工具，同时具备音频提取和语音转文字(ASR)功能。
> 
> **核心优势：不依赖任何第三方API | 无需cookies | 所有操作本地完成**

采用剪贴板监控模式，复制链接即可自动下载。内置faster-whisper语音识别引擎，支持GPU加速识别，可输出txt文字稿和srt字幕双格式。

## 核心功能
- 🎬 **无水印下载** - 支持抖音/B站/小红书/快手等平台
- 🎵 **音频提取** - 一键提取MP3格式音频
- 📝 **语音转文字(ASR)** - faster-whisper语音识别，输出txt+srt双格式
- 🔗 **剪贴板监控** - 复制链接自动下载，无需手动操作
- ⚡ **GPU加速** - 支持CUDA加速识别
- 📦 **多模型选择** - tiny/base/small/medium按需选择
- 🔒 **隐私安全** - 不依赖第三方API，无需cookies，本地处理

## 触发词
视频下载、短视频下载、无水印下载、音频提取、语音转文字、ASR转录

## 使用方式
Python桌面应用，基于tkinter GUI操作：
1. 复制视频链接 → 自动检测并下载
2. 选择"音频转文字"标签页 → 上传音频或输入链接 → 选择模型 → 开始识别
3. 下载完成后自动保存到 downloads 目录

## 安装说明

### 环境要求
- Python 3.10+
- ffmpeg（音视频处理必需）
- NVIDIA CUDA（GPU加速可选，推荐）

### 安装步骤
1. 安装Python依赖：
```bash
pip install yt-dlp requests pyperclip faster-whisper
```

2. 安装ffmpeg：
```bash
# Windows (winget)
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

3. 运行程序：
```bash
python video_downloader.py
```

### Whisper模型选择
| 模型 | 大小 | 显存 | 推荐度 |
|------|------|------|--------|
| tiny | 39M | ~1GB | ⭐ 快速测试 |
| base | 74M | ~1GB | ⭐⭐ 基础识别 |
| small | 244M | ~2GB | ⭐⭐⭐ **推荐首选** |
| medium | 769M | ~5GB | ⭐⭐⭐⭐ 高精度 |

首次使用会自动下载模型（约500MB-3GB）

## 依赖项
- yt-dlp（视频下载）
- faster-whisper（语音识别）
- requests（网络请求）
- pyperclip（剪贴板监控）
- ffmpeg（音视频处理）

## 技术栈
- Python 3.10+
- tkinter（GUI界面）
- faster-whisper / CTranslate2（GPU加速语音识别）

## 版本
1.1.1

## 作者
AI Assistant

## 安全声明
🔒 **隐私优先设计**：
- 不收集任何用户数据
- 所有操作均在本地完成
- 不依赖任何第三方私有API
- 抖音下载采用网页直解析，无需cookies

## 更新日志
- v4.9 (2025-08)：🔒 安全修复：移除api.douyin.wtf第三方API，改为抖音网页直解析；新增AI模型下载确认对话框；添加完整安全声明
- v4.8 (2025-08)：新增"音频工具"标签页；音频格式转换(MP3/WAV/M4A/AAC/OGG/FLAC)；音频裁剪；音频合并；比特率选择
- v4.7 (2025-08)：新增"字幕烧录"标签页；SRT字幕硬烧；自定义字幕样式(字号/颜色/描边/位置)；SRT转ASS转换
- v4.6 (2025-07)：新增"下载历史"标签页；JSON存储；搜索/筛选；右键菜单(删除/重新下载/打开文件夹)
- v4.5 (2025-07)：新增"批量下载"标签页；多链接同时下载；汇总报告
- v4.4 (2025-06)：全新现代化深色主题UI；VS Code风格；GPU状态指示灯
- v4.3 (2025-05)：修复ASR文字稿保存路径；新增设备选择；改进GPU检测；float32精度；HF镜像提前设置

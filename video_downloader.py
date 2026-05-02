#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短视频无水印下载器 - 剪贴板监控版 + 音频转文字
支持平台：抖音、B站、小红书、快手
支持功能：视频下载、音频提取、ASR语音识别

作者：铭晨 ·Vx MingCv1
版本：v4.9.1 - 安全修复：抖音改用yt-dlp方案（开源工具，持续维护），cookies改为可选；移除网页解析方案（反爬失效）

更新说明：
- v4.9.1: 抖音改用yt-dlp开源工具下载（第三方API和网页解析均已失效）；cookies改为可选功能；移除DouyinDownloader中的网页解析方法
- v4.9: 安全修复：移除api.douyin.wtf第三方API依赖，改为直接从抖音网页HTML解析；新增faster-whisper模型下载确认；添加安全声明
- v4.8: 新增"音频工具"标签页；支持音频格式转换（MP3/WAV/M4A/AAC/OGG/FLAC互转）；音频裁剪（设置起止时间）；音频合并（多文件合并）；所有功能基于ffmpeg实现
- v4.7: 新增"字幕烧录"标签页；支持SRT字幕硬烧到视频（ffmpeg）；自定义字幕样式（字号/颜色/描边/位置）；SRT转ASS格式转换；转写完成后可直接烧录
- v4.6: 新增"下载历史"标签页；下载历史JSON存储；支持按标题搜索/按平台筛选；右键菜单（打开文件/文件夹/复制链接/删除记录）；统计信息（今日/总下载数）
- v4.5: 新增"批量下载"标签页，支持多链接同时下载；剪贴板多链接监控提示；成功/失败汇总报告
- v4.4: 全新现代化深色主题UI，类似VS Code风格；圆角按钮和hover效果；渐变进度条；GPU状态指示灯；统一ttk.Style配置

安全声明：
- 本工具不收集任何用户数据
- 所有下载和识别均在本地完成
- 使用开源yt-dlp库访问平台公开内容，不依赖任何第三方私有API
- Cookies为可选功能，仅在部分受限视频时需要
- AI模型来自HuggingFace开源仓库（首次使用需下载）
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import re
import sys
import subprocess
import webbrowser
import json
import requests
import tempfile
import shutil
from datetime import datetime

# 尝试导入yt-dlp
try:
    import yt_dlp
except ImportError:
    print("=" * 50)
    print("错误：未安装 yt-dlp")
    print("请运行以下命令安装：")
    print("pip install yt-dlp")
    print("=" * 50)
    input("按 Enter 键退出...")
    sys.exit(1)

# 尝试导入pyperclip
try:
    import pyperclip
except ImportError:
    print("=" * 50)
    print("警告：未安装 pyperclip，剪贴板监控功能不可用")
    print("请运行以下命令安装：")
    print("pip install pyperclip")
    print("=" * 50)


# ==================== 下载历史管理器 ====================
class DownloadHistoryManager:
    """
    下载历史管理器
    负责历史记录的存储、加载、查询
    """
    
    def __init__(self, history_file_path):
        self.history_file = history_file_path
        self.history = []
        self._ensure_file()
        self.load_history()
    
    def _ensure_file(self):
        """确保历史文件存在"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
        except Exception:
            self.history = []
    
    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def add_record(self, platform, title, file_type, file_path, url):
        """
        添加下载记录
        
        Args:
            platform: 平台名称
            title: 标题
            file_type: 文件类型（视频/音频/文字稿）
            file_path: 文件路径
            url: 原始链接
        """
        record = {
            'id': datetime.now().strftime("%Y%m%d%H%M%S%f"),
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'platform': platform,
            'title': title,
            'file_type': file_type,
            'file_path': file_path,
            'url': url
        }
        self.history.insert(0, record)  # 新记录插入到最前面
        self.save_history()
        return record
    
    def delete_record(self, record_id):
        """删除指定记录"""
        self.history = [r for r in self.history if r['id'] != record_id]
        self.save_history()
    
    def clear_all(self):
        """清空所有记录（不删除文件）"""
        self.history = []
        self.save_history()
    
    def search(self, keyword, platform_filter='全部'):
        """
        搜索历史记录
        
        Args:
            keyword: 搜索关键词
            platform_filter: 平台筛选
        
        Returns:
            筛选后的记录列表
        """
        results = self.history
        
        # 平台筛选
        if platform_filter != '全部':
            results = [r for r in results if r['platform'] == platform_filter]
        
        # 关键词搜索
        if keyword:
            keyword_lower = keyword.lower()
            results = [r for r in results if keyword_lower in r['title'].lower()]
        
        return results
    
    def get_stats(self):
        """
        获取统计信息
        
        Returns:
            dict: {'today': 今日下载数, 'total': 总下载数}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = len([r for r in self.history if r['time'].startswith(today)])
        return {
            'today': today_count,
            'total': len(self.history)
        }


# ==================== ASR 语音识别模块 ====================
class ASREngine:
    """
    音频转文字引擎
    使用 faster-whisper 实现高效的语音识别
    """
    
    # 模型配置：名称 -> (显存需求, 中文推荐度, 描述)
    MODEL_CONFIGS = {
        'tiny': {'vram': '~1GB', 'chinese': '★★★☆☆', 'desc': '极速，适合测试'},
        'base': {'vram': '~1GB', 'chinese': '★★★☆☆', 'desc': '快速，基础识别'},
        'small': {'vram': '~2GB', 'chinese': '★★★★☆', 'desc': '推荐，中文效果好'},
        'medium': {'vram': '~5GB', 'chinese': '★★★★★', 'desc': '高精度，首选推荐'},
    }
    
    def __init__(self):
        self.model = None
        self.current_model_name = None
        self.model_lock = threading.Lock()
        self.current_device = None
        self.current_compute_type = None
    
    @staticmethod
    def check_cuda_available():
        """
        改进的CUDA检测逻辑
        检测顺序：nvidia-smi -> pip安装的nvidia-cublas -> torch.cuda -> ctypes检测cublas
        """
        # 方法1：检查nvidia-smi命令（最可靠，只要有N卡驱动就行）
        try:
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # 方法2：检查pip安装的nvidia-cublas-cu12包
        try:
            import nvidia.cublas
            return True
        except ImportError:
            pass
        
        # 方法3：检查torch.cuda
        try:
            import torch
            if torch.cuda.is_available():
                return True
        except ImportError:
            pass
        
        # 方法4：尝试ctypes加载cublas（支持多版本）
        try:
            import ctypes
            for dll_name in ['cublas64_12.dll', 'cublas64_11.dll', 'cublas64_10.dll']:
                try:
                    ctypes.CDLL(dll_name)
                    return True
                except OSError:
                    continue
        except ImportError:
            pass
        
        return False
    
    def load_model(self, model_size='small', progress_callback=None, device='auto'):
        """
        加载ASR模型
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium)
            progress_callback: 进度回调函数
            device: 设备选择 'auto'/'gpu'/'cpu'
        """
        # 检查设备选择
        cuda_available = self.check_cuda_available()
        
        if device == 'cpu':
            # 强制使用CPU
            use_device = 'cpu'
            use_compute_type = 'int8'
        elif device == 'gpu':
            # 强制使用GPU
            if not cuda_available:
                raise Exception("未检测到CUDA支持。请确保已安装CUDA toolkit。\n\n"
                              "安装方法：\n1. 访问 https://developer.nvidia.com/cuda-downloads\n2. 下载并安装CUDA Toolkit\n3. 重启电脑后重新运行程序")
            use_device = 'cuda'
            use_compute_type = 'float32'  # float32精度更高，避免新显卡float16精度问题
        else:
            # auto模式
            if cuda_available:
                use_device = 'cuda'
                use_compute_type = 'float32'
            else:
                use_device = 'cpu'
                use_compute_type = 'int8'
                if progress_callback:
                    progress_callback(0, "未检测到CUDA，使用CPU模式（较慢但可用）")
        
        # 如果设备或计算类型没变，不需要重新加载
        if (self.model is not None and 
            self.current_model_name == model_size and
            self.current_device == use_device and
            self.current_compute_type == use_compute_type):
            return True
        
        # 检查本地是否有缓存模型
        model_cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        expected_model_path = None
        if os.path.exists(model_cache_dir):
            for item in os.listdir(model_cache_dir):
                if item.startswith(f"models--Systran--faster-whisper-{model_size}"):
                    expected_model_path = os.path.join(model_cache_dir, item)
                    break
        
        model_need_download = expected_model_path is None
        
        # 如果需要下载新模型，弹出确认对话框
        if model_need_download:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            model_info = self.MODEL_CONFIGS.get(model_size, {})
            desc = model_info.get('desc', '')
            vram = model_info.get('vram', '')
            
            confirm = messagebox.askyesno(
                "模型下载确认",
                f"首次使用需要下载AI语音识别模型\n\n"
                f"模型：faster-whisper-{model_size}\n"
                f"显存需求：{vram}\n"
                f"说明：{desc}\n\n"
                f"模型来源：HuggingFace开源仓库\n"
                f"下载地址：https://huggingface.co/Systran/faster-whisper-{model_size}\n\n"
                f"是否现在开始下载？",
                icon='question'
            )
            root.destroy()
            
            if not confirm:
                raise Exception("用户取消模型下载\n请在网络条件良好时再次尝试")
        
        try:
            # 延迟导入，避免启动时卡顿
            from faster_whisper import WhisperModel
            
            if progress_callback:
                progress_callback(0, f"正在加载模型 {model_size}...")
            
            # 设置HuggingFace国内镜像，解决国内网络超时问题
            os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
            # 关闭符号链接警告
            os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
            # 禁用xet传输协议（国内CDN连不上），强制用普通HTTPS走镜像
            os.environ.setdefault('HF_HUB_ENABLE_HF_TRANSFER', '0')
            
            device_desc = "GPU" if use_device == "cuda" else "CPU"
            if progress_callback:
                progress_callback(0, f"使用{device_desc}设备 (compute_type={use_compute_type})...")
            
            # 加载模型
            self.model = WhisperModel(
                model_size,
                device=use_device,
                compute_type=use_compute_type,
                download_root=None,
                cpu_threads=4 if use_device == "cpu" else 0
            )
            
            self.current_model_name = model_size
            self.current_device = use_device
            self.current_compute_type = use_compute_type
            
            if progress_callback:
                progress_callback(100, f"模型 {model_size} 加载完成（{device_desc}）")
            
            return True
            
        except ImportError:
            raise Exception("请先安装 faster-whisper: pip install faster-whisper")
        except Exception as e:
            raise Exception(f"模型加载失败: {str(e)}")
    
    def transcribe(self, audio_path, model_size='small', progress_callback=None, language='zh', device='auto'):
        """
        音频转文字
        
        Args:
            audio_path: 音频文件路径
            model_size: 模型大小 (tiny/base/small/medium)
            progress_callback: 进度回调函数
            language: 语言代码，'zh'为中文
            device: 设备选择 'auto'/'gpu'/'cpu'
        
        Returns:
            dict: {
                'success': bool,
                'text': str,  # 完整文本
                'segments': list,  # 分段结果
                'language': str,  # 检测到的语言
                'duration': float,  # 音频时长
                'save_path': str  # 保存路径
            }
        """
        if progress_callback:
            progress_callback(0, "开始识别...")
        
        # 确保模型已加载，传入device参数
        if self.model is None or self.current_model_name != model_size:
            self.load_model(model_size, progress_callback, device)
        
        try:
            # 执行转写
            if progress_callback:
                progress_callback(10, "正在识别语音...")
            
            segments, info = self.model.transcribe(
                audio_path,
                language=language if language != 'auto' else None,
                beam_size=5,
                vad_filter=True,  # 启用语音活动检测
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            if progress_callback:
                progress_callback(70, "识别完成，正在整理结果...")
            
            # 收集结果
            all_text = []
            segment_list = []
            
            for segment in segments:
                text = segment.text.strip()
                all_text.append(text)
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': text
                })
            
            full_text = ' '.join(all_text)
            
            # 生成输出路径
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            output_dir = os.path.dirname(audio_path)
            txt_path = os.path.join(output_dir, f"{base_name}_文字稿.txt")
            srt_path = os.path.join(output_dir, f"{base_name}_字幕.srt")
            
            # 保存为txt
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"音频转写结果\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"文件：{os.path.basename(audio_path)}\n")
                f.write(f"语言：{info.language} (概率: {info.language_probability:.2%})\n")
                f.write(f"时长：{info.duration:.1f}秒\n")
                f.write(f"模型：{model_size}\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(full_text)
            
            # 保存为srt字幕
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, seg in enumerate(segment_list, 1):
                    start_time = self._format_srt_time(seg['start'])
                    end_time = self._format_srt_time(seg['end'])
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{seg['text']}\n\n")
            
            if progress_callback:
                progress_callback(100, "转写完成！")
            
            return {
                'success': True,
                'text': full_text,
                'segments': segment_list,
                'language': info.language,
                'language_prob': info.language_probability,
                'duration': info.duration,
                'txt_path': txt_path,
                'srt_path': srt_path
            }
            
        except Exception as e:
            raise Exception(f"语音识别失败: {str(e)}")
    
    @staticmethod
    def _format_srt_time(seconds):
        """格式化SRT时间码"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_available_models(self):
        """获取可用模型列表"""
        return self.MODEL_CONFIGS


# ==================== 抖音URL解析器 ====================
class DouyinDownloader:
    """
    抖音视频URL解析器
    仅用于从分享链接提取视频ID，实际下载使用yt-dlp
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
    
    def get_video_id_from_url(self, url):
        """从抖音分享链接提取视频ID"""
        try:
            response = self.session.get(url, allow_redirects=True, timeout=10)
            final_url = response.url
        except Exception:
            final_url = url
        
        patterns = [r'/video/(\d+)', r'/note/(\d+)']
        
        for pattern in patterns:
            match = re.search(pattern, final_url)
            if match:
                return match.group(1)
        
        share_patterns = [r'https?://v\.douyin\.com/[a-zA-Z0-9]+']
        for pattern in share_patterns:
            match = re.search(pattern, url)
            if match:
                short_url = match.group(0)
                try:
                    response = self.session.get(short_url, allow_redirects=True, timeout=10)
                    video_match = re.search(r'/video/(\d+)', response.url)
                    if video_match:
                        return video_match.group(1)
                except:
                    pass
        
        return None


# ==================== 视频下载核心类 ====================
class VideoDownloader:
    """短视频下载器核心类"""
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.script_dir = os.path.dirname(sys.executable)
        else:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = os.path.join(self.script_dir, "downloads", "视频")
        self.audio_dir = os.path.join(self.script_dir, "downloads", "音频")
        self.text_dir = os.path.join(self.script_dir, "downloads", "文字稿")
        self.audio_convert_dir = os.path.join(self.script_dir, "downloads", "音频转换")
        self.download_dir = self.video_dir
        
        for d in [self.video_dir, self.audio_dir, self.text_dir, self.audio_convert_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
        
        self.douyin_downloader = DouyinDownloader()
        self.ffmpeg_available = self._check_ffmpeg()
        self.asr_engine = ASREngine()
        
        # Cookies文件路径（用于抖音等需要认证的平台）
        self.cookies_path = os.path.join(self.script_dir, "cookies.json")
        self._has_cookies = os.path.exists(self.cookies_path)
    
    def _check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符"""
        illegal_chars = r'[\\/:*?"<>|]'
        filename = re.sub(illegal_chars, '_', filename)
        if len(filename) > 200:
            filename = filename[:200]
        filename = filename.strip(' .')
        return filename
    
    def extract_url(self, text):
        """从分享文本中提取URL链接"""
        text = text.strip()
        url_patterns = [
            r'(https?://v\.douyin\.com/[A-Za-z0-9]+/?)',
            r'(https?://www\.douyin\.com/[^\s]+)',
            r'(https?://www\.bilibili\.com/[^\s]+)',
            r'(https?://b23\.tv/[A-Za-z0-9]+)',
            r'(https?://www\.xiaohongshu\.com/[^\s]+)',
            r'(https?://xhslink\.com/[A-Za-z0-9]+)',
            r'(https?://v\.kuaishou\.com/[^\s]+)',
            r'(https?://www\.kuaishou\.com/[^\s]+)',
        ]
        for pattern in url_patterns:
            match = re.search(pattern, text)
            if match:
                url = match.group(1).rstrip(')]}，。！？、')
                return url
        if text.startswith('http'):
            return text
        return None
    
    def detect_platform(self, url):
        """检测视频平台"""
        url_lower = url.lower()
        if 'douyin.com' in url_lower or 'v.douyin.com' in url_lower:
            return '抖音'
        elif 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
            return '哔哩哔哩'
        elif 'xiaohongshu.com' in url_lower or 'xhslink.com' in url_lower:
            return '小红书'
        elif 'kuaishou.com' in url_lower or 'v.kuaishou.com' in url_lower:
            return '快手'
        else:
            return '未知平台'
    
    def download_video(self, url, progress_callback=None):
        """下载视频（所有平台统一使用yt-dlp）"""
        return self._download_ytdlp(url, progress_callback)
    
    def download_audio(self, url, progress_callback=None):
        """提取音频（所有平台统一使用yt-dlp）"""
        return self._download_audio_ytdlp(url, progress_callback)
    
    def download_audio_only(self, url, progress_callback=None):
        """只下载音频用于ASR识别，保存到临时目录，识别后自动清理
        所有平台统一使用yt-dlp"""
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="asr_")
        
        try:
            if not self.ffmpeg_available:
                raise Exception("音频提取需要ffmpeg，请先安装ffmpeg")
            
            info = self._get_video_info_basic(url)
            video_title = info.get('title', 'unknown')
            clean_title = self.clean_filename(video_title)
            output_path = os.path.join(temp_dir, f"{clean_title}.%(ext)s")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [],
                'no_check_certificate': True,
            }
            
            # Cookies为可选功能，仅在部分受限视频时需要
            if self._has_cookies:
                ydl_opts['cookiefile'] = self.cookies_path
            
            if progress_callback:
                def ytdlp_progress_adapter(d):
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        if d['status'] == 'downloading':
                            progress_callback(percent * 0.7, downloaded, total, f"下载进度: {percent:.1f}%")
                        elif d['status'] == 'finished':
                            progress_callback(70, 0, 0, "正在提取音频...")
                    else:
                        progress_callback(0, 0, 0, "下载中...")
                ydl_opts['progress_hooks'].append(ytdlp_progress_adapter)
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # 如果下载失败且没有cookies，提示添加cookies
                if not self._has_cookies:
                    raise Exception(f"视频下载失败，可能是部分视频需要登录。如需登录，请将cookies.json放在程序同目录下。\n\n错误详情: {str(e)}")
                raise
            
            # 查找生成的MP3文件
            for f in os.listdir(temp_dir):
                if f.endswith('.mp3'):
                    if progress_callback:
                        progress_callback(100, 100, 100, "音频提取完成")
                    return {'success': True, 'title': video_title, 'file_path': os.path.join(temp_dir, f), 'temp_dir': temp_dir}
            
            # 没有MP3就找任意音频文件
            for f in os.listdir(temp_dir):
                if progress_callback:
                    progress_callback(100, 100, 100, "下载完成")
                return {'success': True, 'title': video_title, 'file_path': os.path.join(temp_dir, f), 'temp_dir': temp_dir}
            
            raise Exception("音频下载失败：未找到输出文件")
        except Exception as e:
            raise Exception(f"音频提取失败：{str(e)}")
    
    def _download_ytdlp(self, url, progress_callback=None):
        """使用yt-dlp下载视频"""
        info = self._get_video_info_basic(url)
        video_title = info['title']
        clean_title = self.clean_filename(video_title)
        
        output_path = os.path.join(self.video_dir, f"{clean_title}.%(ext)s")
        final_path = os.path.join(self.video_dir, f"{clean_title}.mp4")
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [],
            'merge_output_format': 'mp4',
        }
        
        # Cookies为可选功能，仅在部分受限视频时需要
        if self._has_cookies:
            ydl_opts['cookiefile'] = self.cookies_path
        
        if progress_callback:
            ydl_opts['progress_hooks'].append(lambda d: self._progress_hook(d, progress_callback))
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 查找实际生成的文件
            actual_files = [f for f in os.listdir(self.video_dir) if f.startswith(clean_title)]
            if actual_files:
                final_path = os.path.join(self.video_dir, actual_files[0])
            
            return {
                'success': True,
                'title': video_title,
                'save_path': self.video_dir,
                'file_path': final_path
            }
        except Exception as e:
            # 如果下载失败且没有cookies，提示添加cookies
            if not self._has_cookies:
                raise Exception(f"视频下载失败，可能是部分视频需要登录。如需登录，请将cookies.json放在程序同目录下。\n\n错误详情: {str(e)}")
            raise Exception(f"视频下载失败：{str(e)}")
    
    def _download_audio_ytdlp(self, url, progress_callback=None):
        """使用yt-dlp提取音频"""
        if not self.ffmpeg_available:
            raise Exception("音频提取需要ffmpeg，请先安装ffmpeg")
        
        info = self._get_video_info_basic(url)
        video_title = info['title']
        clean_title = self.clean_filename(video_title)
        
        output_path = os.path.join(self.audio_dir, f"{clean_title}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [],
            'no_check_certificate': True,
        }
        
        # Cookies为可选功能，仅在部分受限视频时需要
        if self._has_cookies:
            ydl_opts['cookiefile'] = self.cookies_path
        
        if progress_callback:
            ydl_opts['progress_hooks'].append(lambda d: self._audio_progress_hook(d, progress_callback))
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 查找实际生成的MP3文件
            mp3_files = [f for f in os.listdir(self.audio_dir) if f.startswith(clean_title) and f.endswith('.mp3')]
            final_path = os.path.join(self.audio_dir, mp3_files[0]) if mp3_files else output_path.replace('%(ext)s', 'mp3')
            
            return {
                'success': True,
                'title': video_title,
                'save_path': self.audio_dir,
                'file_path': final_path
            }
        except Exception as e:
            raise Exception(f"音频提取失败：{str(e)}")
    
    def _progress_hook(self, d, callback):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                callback((downloaded / total) * 100, downloaded, total)
        elif d['status'] == 'finished':
            callback(100, 0, 0)
    
    def _audio_progress_hook(self, d, callback):
        self._progress_hook(d, callback)
    
    def _get_video_info_basic(self, url):
        """获取视频基本信息"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        # Cookies为可选功能，仅在部分受限视频时需要
        if self._has_cookies:
            ydl_opts['cookiefile'] = self.cookies_path
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', '视频'),
                    'platform': self.detect_platform(url)
                }
        except:
            return {
                'title': '视频',
                'platform': self.detect_platform(url)
            }
    
    def transcribe_file(self, file_path, model_size='small', progress_callback=None, language='zh', device='auto'):
        """
        转写音频/视频文件为文字
        
        Args:
            file_path: 音频或视频文件路径
            model_size: 模型大小
            progress_callback: 进度回调
            language: 语言
            device: 设备选择 'auto'/'gpu'/'cpu'
        
        Returns:
            dict: 转写结果
        """
        # 确保ffmpeg可用（用于视频提取音频）
        if not self.ffmpeg_available:
            raise Exception("视频转文字需要ffmpeg支持")
        
        # 如果是视频文件，先提取音频
        video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm']
        audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma']
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in video_exts:
            # 视频文件：先提取音频
            if progress_callback:
                progress_callback(0, "正在从视频提取音频...")
            
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            temp_audio = os.path.join(tempfile.gettempdir(), f"temp_asr_{os.getpid()}.mp3")
            
            try:
                subprocess.run([
                    'ffmpeg', '-i', file_path,
                    '-vn', '-acodec', 'libmp3lame',
                    '-ab', '192k',
                    '-y', temp_audio
                ], check=True, capture_output=True)
                
                # 转写音频
                result = self.asr_engine.transcribe(
                    temp_audio,
                    model_size=model_size,
                    progress_callback=lambda p, m: progress_callback(p * 0.3 + 10, m) if progress_callback else None,
                    language=language,
                    device=device
                )
                
                # 将结果中的临时路径替换为原视频路径
                if result['success']:
                    # 重新保存到正确的位置
                    output_dir = os.path.dirname(file_path)
                    txt_path = os.path.join(output_dir, f"{base_name}_文字稿.txt")
                    srt_path = os.path.join(output_dir, f"{base_name}_字幕.srt")
                    
                    # 更新返回路径
                    result['txt_path'] = txt_path
                    result['srt_path'] = srt_path
                
                return result
                
            finally:
                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except:
                        pass
        
        elif file_ext in audio_exts:
            # 纯音频文件：直接转写
            return self.asr_engine.transcribe(
                file_path,
                model_size=model_size,
                progress_callback=progress_callback,
                language=language,
                device=device
            )
        
        else:
            raise Exception(f"不支持的文件格式: {file_ext}，支持 mp3/wav/m4a/mp4 等")
    
    def move_asr_files_to_text_dir(self, txt_path, srt_path, title):
        """
        将ASR生成的txt和srt文件移动到文字稿目录
        
        Args:
            txt_path: 文字稿文件路径
            srt_path: 字幕文件路径
            title: 标题（用于命名）
        
        Returns:
            dict: {'txt_path': new_txt_path, 'srt_path': new_srt_path}
        """
        clean_title = self.clean_filename(title)
        
        new_txt_path = os.path.join(self.text_dir, f"{clean_title}_文字稿.txt")
        new_srt_path = os.path.join(self.text_dir, f"{clean_title}_字幕.srt")
        
        # 处理重名
        counter = 1
        while os.path.exists(new_txt_path):
            new_txt_path = os.path.join(self.text_dir, f"{clean_title}_文字稿_{counter}.txt")
            counter += 1
        
        counter = 1
        while os.path.exists(new_srt_path):
            new_srt_path = os.path.join(self.text_dir, f"{clean_title}_字幕_{counter}.srt")
            counter += 1
        
        # 移动文件
        if txt_path and os.path.exists(txt_path):
            shutil.move(txt_path, new_txt_path)
        
        if srt_path and os.path.exists(srt_path):
            shutil.move(srt_path, new_srt_path)
        
        return {'txt_path': new_txt_path, 'srt_path': new_srt_path}


# ==================== GUI 界面 ====================
class ClipboardMonitorGUI:
    """剪贴板监控下载器 GUI - v4.6 现代化深色主题 + 批量下载 + 下载历史"""
    
    # 配色方案 - VS Code 风格深色主题
    COLORS = {
        'bg_primary': '#1e1e2e',      # 主背景：深蓝灰
        'bg_secondary': '#2d2d44',     # 卡片/面板背景
        'bg_tertiary': '#3d3d5c',     # 悬停/高亮背景
        'text_primary': '#e0e0e0',    # 主要文字
        'text_secondary': '#a0a0b0',  # 次要文字
        'accent': '#7c3aed',           # 强调色：紫色
        'accent_hover': '#8b5cf6',    # 强调色悬停
        'success': '#4CAF50',         # 成功色：绿色
        'warning': '#FF9800',         # 警告色：橙色
        'error': '#ef4444',           # 错误色：红色
        'border': '#3d3d5c',          # 边框色
        'log_bg': '#0d1117',          # 日志背景：更深的黑
    }
    
    def __init__(self):
        self.downloader = VideoDownloader()
        self.monitoring = True
        self.last_clipboard = ""
        self.processed_urls = []
        self.check_timer = None
        self.asr_task_running = False
        
        # 初始化CUDA检测结果
        self.cuda_available = ASREngine.check_cuda_available()
        
        # 初始化下载历史管理器
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        history_file = os.path.join(script_dir, "downloads", "download_history.json")
        self.history_manager = DownloadHistoryManager(history_file)
        
        self.root = tk.Tk()
        self.root.title("🎬 短视频无水印下载器 v4.9")
        self.root.geometry("800x720")
        self.root.minsize(750, 620)
        self.root.resizable(True, True)
        
        # 设置整体风格
        self.setup_styles()
        self.setup_ui()
        self.start_monitoring()
    
    def setup_styles(self):
        """配置ttk主题和样式"""
        style = ttk.Style(self.root)
        
        # 使用默认主题并自定义
        style.theme_use('clam')
        
        # 全局背景色
        self.root.configure(bg=self.COLORS['bg_primary'])
        
        # 配置 Frame 样式
        style.configure('TFrame', background=self.COLORS['bg_primary'])
        style.configure('Card.TFrame', background=self.COLORS['bg_secondary'])
        
        # 配置 LabelFrame 样式
        style.configure('TLabelframe', 
                       background=self.COLORS['bg_secondary'],
                       foreground=self.COLORS['text_primary'],
                       bordercolor=self.COLORS['border'],
                       relief='flat')
        style.configure('TLabelframe.Label',
                       background=self.COLORS['bg_secondary'],
                       foreground=self.COLORS['text_primary'],
                       font=('Microsoft YaHei UI', 10, 'bold'))
        
        # 配置 Label 样式
        style.configure('TLabel',
                       background=self.COLORS['bg_primary'],
                       foreground=self.COLORS['text_primary'],
                       font=('Microsoft YaHei UI', 10))
        
        # 配置 Button 样式 - 圆角按钮
        style.configure('TButton',
                       background=self.COLORS['accent'],
                       foreground=self.COLORS['text_primary'],
                       bordercolor=self.COLORS['accent'],
                       lightcolor=self.COLORS['accent'],
                       darkcolor=self.COLORS['accent'],
                       font=('Microsoft YaHei UI', 10),
                       padding=(15, 8))
        style.map('TButton',
                 background=[('active', self.COLORS['accent_hover']), ('pressed', self.COLORS['accent'])],
                 foreground=[('active', self.COLORS['text_primary'])])
        
        # Accent 按钮样式（主要操作按钮）
        style.configure('Accent.TButton',
                       background=self.COLORS['accent'],
                       foreground='#ffffff',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(20, 10))
        style.map('Accent.TButton',
                 background=[('active', self.COLORS['accent_hover']), ('pressed', self.COLORS['accent'])])
        
        # Success 按钮样式
        style.configure('Success.TButton',
                       background=self.COLORS['success'],
                       foreground='#ffffff',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(15, 8))
        style.map('Success.TButton',
                 background=[('active', '#5cbf60'), ('pressed', self.COLORS['success'])])
        
        # Warning 按钮样式
        style.configure('Warning.TButton',
                       background=self.COLORS['warning'],
                       foreground='#ffffff',
                       font=('Microsoft YaHei UI', 10),
                       padding=(15, 8))
        style.map('Warning.TButton',
                 background=[('active', '#ffad33'), ('pressed', self.COLORS['warning'])])
        
        # 配置 Entry 样式
        style.configure('TEntry',
                       fieldbackground=self.COLORS['bg_tertiary'],
                       foreground=self.COLORS['text_primary'],
                       bordercolor=self.COLORS['border'],
                       lightcolor=self.COLORS['border'],
                       darkcolor=self.COLORS['border'],
                       insertcolor=self.COLORS['text_primary'],
                       font=('Microsoft YaHei UI', 10))
        
        # 配置 Combobox 样式
        style.configure('TCombobox',
                       fieldbackground=self.COLORS['bg_tertiary'],
                       background=self.COLORS['bg_tertiary'],
                       foreground=self.COLORS['text_primary'],
                       bordercolor=self.COLORS['border'],
                       arrowcolor=self.COLORS['text_primary'],
                       font=('Microsoft YaHei UI', 10))
        style.map('TCombobox',
                 fieldbackground=[('readonly', self.COLORS['bg_tertiary'])],
                 selectbackground=[('readonly', self.COLORS['accent'])],
                 selectforeground=[('readonly', '#ffffff')])
        
        # 配置 Notebook 样式
        style.configure('TNotebook',
                       background=self.COLORS['bg_primary'],
                       bordercolor=self.COLORS['bg_primary'])
        style.configure('TNotebook.Tab',
                       background=self.COLORS['bg_secondary'],
                       foreground=self.COLORS['text_secondary'],
                       padding=[20, 10],
                       font=('Microsoft YaHei UI', 10))
        style.map('TNotebook.Tab',
                 background=[('selected', self.COLORS['bg_primary']), ('active', self.COLORS['bg_tertiary'])],
                 foreground=[('selected', self.COLORS['text_primary']), ('active', self.COLORS['text_primary'])])
        
        # 配置 Treeview 样式（用于表格）
        style.configure('Treeview',
                       background=self.COLORS['bg_secondary'],
                       foreground=self.COLORS['text_primary'],
                       fieldbackground=self.COLORS['bg_secondary'],
                       bordercolor=self.COLORS['border'],
                       font=('Microsoft YaHei UI', 9))
        style.map('Treeview',
                 background=[('selected', self.COLORS['accent'])],
                 foreground=[('selected', '#ffffff')])
        style.configure('Treeview.Heading',
                       background=self.COLORS['bg_tertiary'],
                       foreground=self.COLORS['text_primary'],
                       font=('Microsoft YaHei UI', 9, 'bold'))
        
        # 配置 Progressbar 样式 - 渐变色效果
        style.configure('Gradient.Horizontal.TProgressbar',
                       background=self.COLORS['accent'],
                       troughcolor=self.COLORS['bg_tertiary'],
                       bordercolor=self.COLORS['bg_secondary'],
                       thickness=8)
    
    def setup_ui(self):
        """设置界面布局"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        # === 下载 tab ===
        self.download_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.download_tab, text="  📥 下载模式 ")
        self.setup_download_tab()
        
        # === 批量下载 tab ===
        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text="  📦 批量下载 ")
        self.setup_batch_tab()
        
        # === ASR tab ===
        self.asr_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.asr_tab, text="  🎤 音频转文字 ")
        self.setup_asr_tab()
        
        # === 下载历史 tab ===
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="  📜 下载历史 ")
        self.setup_history_tab()
        
        # === 字幕烧录 tab ===
        self.subtitle_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.subtitle_tab, text="  🔥 字幕烧录 ")
        self.setup_subtitle_tab()
        
        # === 音频工具 tab ===
        self.audio_tool_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.audio_tool_tab, text="  🎵 音频工具 ")
        self.setup_audio_tool_tab()
    
    def setup_download_tab(self):
        """设置下载标签页"""
        main_frame = ttk.Frame(self.download_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 主标题
        title_label = tk.Label(
            title_frame,
            text="🎬 短视频无水印下载器",
            font=("Microsoft YaHei UI", 22, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        # 版本号标签
        version_label = tk.Label(
            title_frame,
            text="v4.9",
            font=("Consolas", 12, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary'],
            padx=10, pady=4,
            relief='solid',
            bd=1
        )
        version_label.pack(side=tk.RIGHT)
        
        # 副标题
        subtitle_label = tk.Label(
            title_frame,
            text="复制视频链接后自动下载 · 支持抖音/B站/小红书/快手",
            font=("Microsoft YaHei UI", 9),
            foreground=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_primary']
        )
        subtitle_label.pack(side=tk.BOTTOM, anchor=tk.W, pady=(5, 0))
        
        # 作者标识
        author_label = tk.Label(
            title_frame,
            text="作者：铭晨 ·Vx MingCv1",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary']
        )
        author_label.pack(side=tk.RIGHT, padx=(15, 0))
        
        # ========== 监控状态卡片 ==========
        status_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat', bd=0)
        status_card.pack(fill=tk.X, pady=(0, 15))
        
        # 圆角效果用 Canvas 绘制
        canvas_status = tk.Canvas(status_card, bg=self.COLORS['bg_secondary'], 
                                   highlightthickness=0, height=70)
        canvas_status.pack(fill=tk.X, padx=0, pady=0)
        
        # 绘制背景
        canvas_status.create_rectangle(0, 0, 800, 70, fill=self.COLORS['bg_secondary'], outline="")
        
        # 监控状态标签
        self.status_canvas = canvas_status
        self.status_indicator = canvas_status.create_oval(20, 25, 40, 45, fill=self.COLORS['success'], outline="")
        self.status_text = canvas_status.create_text(55, 35, text="监控中", 
                                                      font=("Microsoft YaHei UI", 14, "bold"),
                                                      fill=self.COLORS['success'], anchor="w")
        
        # 已处理数量
        self.record_label = canvas_status.create_text(200, 35, text=f"已处理: 0 个链接",
                                                       font=("Microsoft YaHei UI", 10),
                                                       fill=self.COLORS['text_secondary'], anchor="w")
        
        # 暂停/继续按钮
        self.pause_btn = ttk.Button(status_card, text="⏸️ 暂停", 
                                    command=self.toggle_monitoring, width=10)
        canvas_status.create_window(650, 35, window=self.pause_btn, anchor="center")
        
        # ffmpeg状态
        ffmpeg_status = "✅ ffmpeg可用" if self.downloader.ffmpeg_available else "⚠️ ffmpeg不可用"
        self.ffmpeg_label = canvas_status.create_text(20, 55, text=ffmpeg_status,
                                                       font=("Microsoft YaHei UI", 9),
                                                       fill=self.COLORS['success'] if self.downloader.ffmpeg_available else self.COLORS['warning'],
                                                       anchor="w")
        
        # ========== 日志区域 ==========
        log_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        log_label = tk.Label(log_card, text="📋  运行日志",
                             font=("Microsoft YaHei UI", 11, "bold"),
                             foreground=self.COLORS['text_primary'],
                             bg=self.COLORS['bg_secondary'],
                             anchor='w')
        log_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(
            log_card, wrap=tk.WORD, 
            font=("JetBrains Mono", 10),  # 等宽字体，代码风格
            relief=tk.FLAT, 
            bg=self.COLORS['log_bg'],  # 深色背景
            fg="#00ff88",  # 亮绿色文字
            insertbackground=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            padx=10, pady=10,
            state='disabled'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 日志标签配置 - 代码风格配色
        self.log_text.tag_configure("info", foreground="#00ff88")       # 亮绿
        self.log_text.tag_configure("warning", foreground=self.COLORS['warning'])  # 橙色
        self.log_text.tag_configure("error", foreground=self.COLORS['error'])        # 红色
        self.log_text.tag_configure("success", foreground="#69f0ae")    # 亮绿
        self.log_text.tag_configure("platform_douyin", foreground="#40c4ff")  # 青色
        self.log_text.tag_configure("platform_bilibili", foreground="#ff6e40")  # 橙色
        self.log_text.tag_configure("platform_xiaohongshu", foreground="#ff4081")  # 粉色
        self.log_text.tag_configure("platform_kuaishou", foreground="#ffff00")  # 黄色
        
        # ========== 底部按钮区 ==========
        footer_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        footer_frame.pack(fill=tk.X)
        
        btn_style_frame = tk.Frame(footer_frame, bg=self.COLORS['bg_primary'])
        btn_style_frame.pack(side=tk.LEFT)
        
        ttk.Button(btn_style_frame, text="📂 视频文件夹", 
                   command=self.open_video_folder).pack(side=tk.LEFT)
        ttk.Button(btn_style_frame, text="🎵 音频文件夹", 
                   command=self.open_audio_folder).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_style_frame, text="🗑️ 清空日志", 
                   command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(btn_style_frame, text="🔄 清空已处理", 
                   command=self.clear_processed).pack(side=tk.LEFT, padx=8)
        
        # 平台标签
        platforms_frame = tk.Frame(footer_frame, bg=self.COLORS['bg_primary'])
        platforms_frame.pack(side=tk.RIGHT)
        
        tk.Label(platforms_frame, text="🏷️ 支持：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_primary']).pack(side=tk.LEFT)
        
        platforms = [("抖音", "#40c4ff"), ("B站", "#ff6e40"), ("小红书", "#ff4081"), ("快手", "#ffff00")]
        for platform, color in platforms:
            chip = tk.Label(platforms_frame, text=platform,
                           bg=self.COLORS['bg_tertiary'],
                           fg=color,
                           padx=10, pady=3,
                           font=("Microsoft YaHei UI", 9, "bold"),
                           relief='solid', bd=1)
            chip.pack(side=tk.LEFT, padx=3)
    
    def setup_asr_tab(self):
        """设置ASR标签页"""
        main_frame = ttk.Frame(self.asr_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="🎤 音频转文字 (ASR)",
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        version_badge = tk.Label(
            title_frame,
            text="v4.9",
            font=("Consolas", 10, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary'],
            padx=8, pady=3,
            relief='solid', bd=1
        )
        version_badge.pack(side=tk.RIGHT)
        
        # ========== 使用说明卡片 ==========
        info_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        info_card.pack(fill=tk.X, pady=(0, 15))
        
        info_label = tk.Label(info_card, text="📖 使用说明",
                             font=("Microsoft YaHei UI", 11, "bold"),
                             foreground=self.COLORS['text_primary'],
                             bg=self.COLORS['bg_secondary'],
                             anchor='w')
        info_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        info_text = """• 方式一：选择本地音频/视频文件进行转文字
• 方式二：输入视频链接，自动下载并转文字
• 支持格式：MP3、WAV、M4A、MP4、AVI等
• 输出结果：文字稿(.txt) + 字幕(.srt) → 保存到"文字稿"文件夹
• AI模型来自HuggingFace开源仓库，首次使用需下载"""
        
        tk.Label(info_card, text=info_text,
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary'],
                justify=tk.LEFT, anchor='w').pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # ========== 文件选择区域 ==========
        file_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        file_card.pack(fill=tk.X, pady=(0, 15))
        
        file_label = tk.Label(file_card, text="📁 选择文件 / 链接输入",
                             font=("Microsoft YaHei UI", 11, "bold"),
                             foreground=self.COLORS['text_primary'],
                             bg=self.COLORS['bg_secondary'],
                             anchor='w')
        file_label.pack(fill=tk.X, padx=12, pady=(10, 8))
        
        # 文件路径输入
        file_input_frame = tk.Frame(file_card, bg=self.COLORS['bg_secondary'])
        file_input_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        
        self.asr_file_path = tk.StringVar()
        entry_style = tk.Entry(file_input_frame, textvariable=self.asr_file_path,
                               font=("Microsoft YaHei UI", 10),
                               bg=self.COLORS['bg_tertiary'],
                               fg=self.COLORS['text_primary'],
                               insertbackground=self.COLORS['text_primary'],
                               relief='flat', bd=0)
        entry_style.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        
        ttk.Button(file_input_frame, text="浏览...",
                   command=self.browse_asr_file).pack(side=tk.RIGHT, padx=(8, 0))
        
        # 链接输入
        link_frame = tk.Frame(file_card, bg=self.COLORS['bg_secondary'])
        link_frame.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        tk.Label(link_frame, text="🔗 视频链接：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.asr_link = tk.StringVar()
        link_entry = tk.Entry(link_frame, textvariable=self.asr_link,
                              font=("Microsoft YaHei UI", 10),
                              bg=self.COLORS['bg_tertiary'],
                              fg=self.COLORS['text_primary'],
                              insertbackground=self.COLORS['text_primary'],
                              relief='flat', bd=0)
        link_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, ipady=6)
        
        # ========== 模型设置卡片 ==========
        model_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        model_card.pack(fill=tk.X, pady=(0, 15))
        
        model_label = tk.Label(model_card, text="⚙️ 模型设置",
                              font=("Microsoft YaHei UI", 11, "bold"),
                              foreground=self.COLORS['text_primary'],
                              bg=self.COLORS['bg_secondary'],
                              anchor='w')
        model_label.pack(fill=tk.X, padx=12, pady=(10, 8))
        
        # 模型选择行
        model_row = tk.Frame(model_card, bg=self.COLORS['bg_secondary'])
        model_row.pack(fill=tk.X, padx=12, pady=(0, 8))
        
        tk.Label(model_row, text="🤖 模型大小：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.asr_model_var = tk.StringVar(value='small')
        model_combo = ttk.Combobox(
            model_row,
            textvariable=self.asr_model_var,
            values=['tiny', 'base', 'small', 'medium'],
            state='readonly',
            width=12
        )
        model_combo.pack(side=tk.LEFT, padx=8)
        
        tk.Label(model_row, text="推荐 small/medium（中文效果好）",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        # 语言选择行
        lang_row = tk.Frame(model_card, bg=self.COLORS['bg_secondary'])
        lang_row.pack(fill=tk.X, padx=12, pady=(0, 8))
        
        tk.Label(lang_row, text="🌐 识别语言：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.asr_lang_var = tk.StringVar(value='zh')
        lang_combo = ttk.Combobox(
            lang_row,
            textvariable=self.asr_lang_var,
            values=[('zh', '中文'), ('en', '英文'), ('auto', '自动检测')],
            state='readonly',
            width=15
        )
        lang_combo.pack(side=tk.LEFT, padx=8)
        
        # 设备选择行 + GPU状态指示灯
        device_row = tk.Frame(model_card, bg=self.COLORS['bg_secondary'])
        device_row.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        tk.Label(device_row, text="🖥️ 运行设备：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        # 检测CUDA状态并设置默认值
        if self.cuda_available:
            default_device = 'auto'
        else:
            default_device = 'cpu'
        
        self.asr_device_var = tk.StringVar(value=default_device)
        device_combo = ttk.Combobox(
            device_row,
            textvariable=self.asr_device_var,
            values=[('auto', 'Auto (自动)'), ('gpu', 'GPU (加速)'), ('cpu', 'CPU (兼容)')],
            state='readonly',
            width=18
        )
        device_combo.pack(side=tk.LEFT, padx=8)
        
        # GPU状态指示灯
        self.gpu_indicator_canvas = tk.Canvas(device_row, width=20, height=20,
                                              bg=self.COLORS['bg_secondary'],
                                              highlightthickness=0)
        self.gpu_indicator_canvas.pack(side=tk.LEFT, padx=(5, 0))
        
        # 绘制指示灯
        indicator_color = self.COLORS['success'] if self.cuda_available else self.COLORS['error']
        self.gpu_indicator = self.gpu_indicator_canvas.create_oval(2, 2, 18, 18,
                                                                    fill=indicator_color,
                                                                    outline="")
        # 发光效果
        self.gpu_indicator_canvas.create_oval(5, 5, 15, 15,
                                              fill=indicator_color,
                                              outline="")
        
        # GPU状态文字
        gpu_text = "GPU可用 ✅" if self.cuda_available else "GPU不可用 ❌"
        self.gpu_status_label = tk.Label(device_row, text=gpu_text,
                                         font=("Microsoft YaHei UI", 9, "bold"),
                                         foreground=indicator_color,
                                         bg=self.COLORS['bg_secondary'])
        self.gpu_status_label.pack(side=tk.LEFT, padx=5)
        
        if self.cuda_available:
            hint_text = "（推荐GPU加速）"
        else:
            hint_text = "（将使用CPU模式）"
        tk.Label(device_row, text=hint_text,
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        # ========== 开始按钮和进度 ==========
        btn_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.asr_start_btn = ttk.Button(
            btn_frame,
            text="🎤 开始转写",
            command=self.start_asr_task,
            style="Accent.TButton"
        )
        self.asr_start_btn.pack(side=tk.LEFT)
        
        # 进度条
        self.asr_progress = ttk.Progressbar(
            btn_frame,
            mode='determinate',
            length=300,
            style='Gradient.Horizontal.TProgressbar'
        )
        self.asr_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)
        
        self.asr_progress_var = tk.StringVar(value="")
        self.asr_progress_label = tk.Label(btn_frame, textvariable=self.asr_progress_var,
                                           font=("Microsoft YaHei UI", 10),
                                           foreground=self.COLORS['success'],
                                           bg=self.COLORS['bg_primary'])
        self.asr_progress_label.pack(side=tk.LEFT, padx=10)
        
        # ========== 日志区域 ==========
        log_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        log_label = tk.Label(log_card, text="📋 识别日志",
                            font=("Microsoft YaHei UI", 11, "bold"),
                            foreground=self.COLORS['text_primary'],
                            bg=self.COLORS['bg_secondary'],
                            anchor='w')
        log_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        self.asr_log = scrolledtext.ScrolledText(
            log_card, wrap=tk.WORD, font=("JetBrains Mono", 10),  # 等宽字体
            relief=tk.FLAT, bg=self.COLORS['log_bg'], fg="#00ff88",
            insertbackground=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            padx=10, pady=10,
            height=8,
            state='disabled'
        )
        self.asr_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.asr_log.tag_configure("info", foreground="#00ff88")
        self.asr_log.tag_configure("warning", foreground=self.COLORS['warning'])
        self.asr_log.tag_configure("error", foreground=self.COLORS['error'])
        self.asr_log.tag_configure("success", foreground="#69f0ae")
        
        # ========== 结果预览区域 ==========
        result_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        result_card.pack(fill=tk.BOTH, expand=True)
        
        result_label = tk.Label(result_card, text="📝 转写结果预览",
                               font=("Microsoft YaHei UI", 11, "bold"),
                               foreground=self.COLORS['text_primary'],
                               bg=self.COLORS['bg_secondary'],
                               anchor='w')
        result_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        # 预览框 - 更醒目的样式
        self.asr_result = scrolledtext.ScrolledText(
            result_card, wrap=tk.WORD, font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT, 
            bg=self.COLORS['bg_tertiary'],  # 稍微浅一点的背景
            fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            padx=10, pady=10,
            height=6,
            state='disabled'
        )
        self.asr_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    def setup_batch_tab(self):
        """设置批量下载标签页"""
        main_frame = ttk.Frame(self.batch_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="📦 批量下载",
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        version_badge = tk.Label(
            title_frame,
            text="v4.9",
            font=("Consolas", 10, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary'],
            padx=8, pady=3,
            relief='solid', bd=1
        )
        version_badge.pack(side=tk.RIGHT)
        
        # ========== 使用说明卡片 ==========
        info_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        info_card.pack(fill=tk.X, pady=(0, 15))
        
        info_label = tk.Label(info_card, text="📖 使用说明",
                             font=("Microsoft YaHei UI", 11, "bold"),
                             foreground=self.COLORS['text_primary'],
                             bg=self.COLORS['bg_secondary'],
                             anchor='w')
        info_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        info_text = """• 每行输入一个视频链接（支持抖音、B站、小红书、快手）
• 支持粘贴分享文本，自动提取链接
• 同时下载视频+音频
• 逐个下载，显示每个的进度和状态"""
        
        tk.Label(info_card, text=info_text,
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary'],
                justify=tk.LEFT, anchor='w').pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # ========== 链接输入区域 ==========
        input_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        input_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        input_label = tk.Label(input_card, text="🔗 输入链接（每行一个）",
                              font=("Microsoft YaHei UI", 11, "bold"),
                              foreground=self.COLORS['text_primary'],
                              bg=self.COLORS['bg_secondary'],
                              anchor='w')
        input_label.pack(fill=tk.X, padx=12, pady=(10, 8))
        
        # 链接输入文本框（多行）
        self.batch_text_frame = tk.Frame(input_card, bg=self.COLORS['bg_secondary'])
        self.batch_text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        
        self.batch_text = tk.Text(
            self.batch_text_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            relief='flat',
            padx=10,
            pady=10,
            height=8
        )
        self.batch_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加占位提示
        self.batch_text.insert(1.0, "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx")
        self.batch_text.bind('<FocusIn>', self._on_batch_text_focus_in)
        self.batch_text.bind('<FocusOut>', self._on_batch_text_focus_out)
        
        # ========== 操作按钮区域 ==========
        btn_card = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        btn_card.pack(fill=tk.X, pady=(0, 15))
        
        # 开始按钮
        self.batch_start_btn = ttk.Button(
            btn_card,
            text="🚀 开始批量下载",
            command=self.start_batch_download,
            style="Accent.TButton"
        )
        self.batch_start_btn.pack(side=tk.LEFT)
        
        # 停止按钮
        self.batch_stop_btn = ttk.Button(
            btn_card,
            text="⏹️ 停止",
            command=self.stop_batch_download,
            state='disabled'
        )
        self.batch_stop_btn.pack(side=tk.LEFT, padx=8)
        
        # 清空按钮
        ttk.Button(btn_card, text="🗑️ 清空输入",
                   command=self.clear_batch_input).pack(side=tk.LEFT, padx=8)
        
        # 进度标签
        self.batch_progress_label = tk.Label(
            btn_card, text="",
            font=("Microsoft YaHei UI", 10, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        self.batch_progress_label.pack(side=tk.RIGHT)
        
        # ========== 结果表格区域 ==========
        result_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        result_card.pack(fill=tk.BOTH, expand=True)
        
        result_label = tk.Label(result_card, text="📋 下载结果",
                              font=("Microsoft YaHei UI", 11, "bold"),
                              foreground=self.COLORS['text_primary'],
                              bg=self.COLORS['bg_secondary'],
                              anchor='w')
        result_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        # 表格
        table_frame = tk.Frame(result_card, bg=self.COLORS['bg_secondary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        
        # 创建Treeview表格
        columns = ('序号', '链接', '平台', '状态', '文件名')
        self.batch_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8)
        
        # 设置列宽
        self.batch_tree.heading('序号', text='序号')
        self.batch_tree.heading('链接', text='链接')
        self.batch_tree.heading('平台', text='平台')
        self.batch_tree.heading('状态', text='状态')
        self.batch_tree.heading('文件名', text='文件名')
        
        self.batch_tree.column('序号', width=50, anchor='center')
        self.batch_tree.column('链接', width=250, anchor='w')
        self.batch_tree.column('平台', width=80, anchor='center')
        self.batch_tree.column('状态', width=80, anchor='center')
        self.batch_tree.column('文件名', width=200, anchor='w')
        
        # 滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=vsb.set)
        
        self.batch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ========== 汇总信息 ==========
        summary_frame = tk.Frame(result_card, bg=self.COLORS['bg_secondary'])
        summary_frame.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        self.batch_summary_label = tk.Label(
            summary_frame, text="",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=self.COLORS['bg_secondary']
        )
        self.batch_summary_label.pack(side=tk.LEFT)
        
        # 初始化批量下载状态
        self.batch_running = False
        self.batch_stop_flag = False
        self.batch_urls = []  # 当前批次URL列表
        self.batch_results = []  # 存储下载结果
    
    def setup_subtitle_tab(self):
        """设置字幕烧录标签页"""
        main_frame = ttk.Frame(self.subtitle_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="🔥 字幕烧录",
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        # ========== 使用说明 ==========
        info_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        info_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(info_card, text="📖 使用说明",
                font=("Microsoft YaHei UI", 11, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary'],
                anchor='w').pack(fill=tk.X, padx=12, pady=(10, 5))
        
        info_text = """• 选择视频文件和SRT字幕文件，将字幕硬烧到视频中
• 也支持SRT转ASS格式（ASS支持更丰富的样式）
• ASR转写完成后可直接从"音频转文字"页跳转烧录
• 需要ffmpeg支持"""
        
        tk.Label(info_card, text=info_text,
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary'],
                justify=tk.LEFT, anchor='w').pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # ========== 文件选择区域 ==========
        file_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        file_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(file_card, text="📁 文件选择",
                font=("Microsoft YaHei UI", 11, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary'],
                anchor='w').pack(fill=tk.X, padx=12, pady=(10, 5))
        
        # 视频文件选择
        video_frame = tk.Frame(file_card, bg=self.COLORS['bg_secondary'])
        video_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(video_frame, text="视频文件：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.subtitle_video_path = tk.StringVar()
        ttk.Entry(video_frame, textvariable=self.subtitle_video_path,
                 font=("Microsoft YaHei UI", 10), width=45).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(video_frame, text="浏览...",
                  command=self._browse_video_for_subtitle).pack(side=tk.LEFT)
        
        # 字幕文件选择
        srt_frame = tk.Frame(file_card, bg=self.COLORS['bg_secondary'])
        srt_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(srt_frame, text="字幕文件：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.subtitle_srt_path = tk.StringVar()
        ttk.Entry(srt_frame, textvariable=self.subtitle_srt_path,
                 font=("Microsoft YaHei UI", 10), width=45).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(srt_frame, text="浏览...",
                  command=self._browse_srt_file).pack(side=tk.LEFT)
        
        # 从ASR结果填充
        hint_frame = tk.Frame(file_card, bg=self.COLORS['bg_secondary'])
        hint_frame.pack(fill=tk.X, padx=12, pady=(0, 10))
        tk.Label(hint_frame, text="💡 ASR转写完成后，字幕文件会自动填入",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        # ========== 字幕样式配置 ==========
        style_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        style_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(style_card, text="🎨 字幕样式",
                font=("Microsoft YaHei UI", 11, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary'],
                anchor='w').pack(fill=tk.X, padx=12, pady=(10, 5))
        
        style_frame = tk.Frame(style_card, bg=self.COLORS['bg_secondary'])
        style_frame.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # 字体大小
        tk.Label(style_frame, text="字号：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).grid(row=0, column=0, padx=5)
        self.subtitle_font_size = tk.StringVar(value="中")
        ttk.Combobox(style_frame, textvariable=self.subtitle_font_size,
                    values=["小", "中", "大"], width=5, state='readonly').grid(row=0, column=1, padx=5)
        
        # 字体颜色
        tk.Label(style_frame, text="颜色：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).grid(row=0, column=2, padx=5)
        self.subtitle_font_color = tk.StringVar(value="白")
        ttk.Combobox(style_frame, textvariable=self.subtitle_font_color,
                    values=["白", "黄", "绿", "青"], width=5, state='readonly').grid(row=0, column=3, padx=5)
        
        # 描边
        tk.Label(style_frame, text="描边：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).grid(row=0, column=4, padx=5)
        self.subtitle_outline = tk.StringVar(value="黑")
        ttk.Combobox(style_frame, textvariable=self.subtitle_outline,
                    values=["黑", "无"], width=5, state='readonly').grid(row=0, column=5, padx=5)
        
        # 位置
        tk.Label(style_frame, text="位置：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).grid(row=0, column=6, padx=5)
        self.subtitle_position = tk.StringVar(value="底部")
        ttk.Combobox(style_frame, textvariable=self.subtitle_position,
                    values=["底部", "顶部"], width=5, state='readonly').grid(row=0, column=7, padx=5)
        
        # ========== 操作按钮 ==========
        btn_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.burn_btn = ttk.Button(
            btn_frame,
            text="🔥 烧录字幕到视频",
            command=self.start_subtitle_burn,
            style="Accent.TButton"
        )
        self.burn_btn.pack(side=tk.LEFT)
        
        self.srt_to_ass_btn = ttk.Button(
            btn_frame,
            text="📝 SRT转ASS",
            command=self.convert_srt_to_ass,
            style="TButton"
        )
        self.srt_to_ass_btn.pack(side=tk.LEFT, padx=10)
        
        # 进度条
        self.burn_progress = ttk.Progressbar(
            btn_frame,
            mode='determinate',
            length=250,
            style='Gradient.Horizontal.TProgressbar'
        )
        self.burn_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)
        
        self.burn_progress_var = tk.StringVar(value="")
        tk.Label(btn_frame, textvariable=self.burn_progress_var,
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['success'],
                bg=self.COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        
        # ========== 日志区域 ==========
        log_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        log_card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(log_card, text="📋 烧录日志",
                font=("Microsoft YaHei UI", 11, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary'],
                anchor='w').pack(fill=tk.X, padx=12, pady=(10, 5))
        
        self.burn_log = scrolledtext.ScrolledText(
            log_card, wrap=tk.WORD, font=("JetBrains Mono", 10),
            relief=tk.FLAT, bg=self.COLORS['log_bg'], fg="#00ff88",
            insertbackground=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            padx=10, pady=10,
            height=10,
            state='disabled'
        )
        self.burn_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.burn_log.tag_configure("info", foreground="#00ff88")
        self.burn_log.tag_configure("warning", foreground=self.COLORS['warning'])
        self.burn_log.tag_configure("error", foreground=self.COLORS['error'])
        self.burn_log.tag_configure("success", foreground="#69f0ae")
        
        # 保存最近一次ASR的srt路径（供烧录使用）
        self.last_asr_srt_path = None
        self.last_asr_video_path = None
    
    def _browse_video_for_subtitle(self):
        """浏览选择视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov *.flv"), ("所有文件", "*.*")]
        )
        if file_path:
            self.subtitle_video_path.set(file_path)
    
    def _browse_srt_file(self):
        """浏览选择字幕文件"""
        file_path = filedialog.askopenfilename(
            title="选择字幕文件",
            filetypes=[("字幕文件", "*.srt *.ass"), ("所有文件", "*.*")]
        )
        if file_path:
            self.subtitle_srt_path.set(file_path)
    
    def _get_subtitle_force_style(self):
        """根据用户选择生成ffmpeg force_style参数"""
        font_size_map = {"小": 16, "中": 24, "大": 32}
        font_color_map = {"白": "&H00FFFFFF", "黄": "&H0000FFFF", "绿": "&H0000FF00", "青": "&H00FFFF00"}
        outline_map = {"黑": 2, "无": 0}
        position_map = {"底部": 10, "顶部": 90}
        
        fontsize = font_size_map.get(self.subtitle_font_size.get(), 24)
        primarycolour = font_color_map.get(self.subtitle_font_color.get(), "&H00FFFFFF")
        outline = outline_map.get(self.subtitle_outline.get(), 2)
        marginv = position_map.get(self.subtitle_position.get(), 10)
        
        return (f"FontName=Microsoft YaHei UI,FontSize={fontsize},"
                f"PrimaryColour={primarycolour},OutlineColour=&H00000000,"
                f"BackColour=&H80000000,BorderStyle=1,Outline={outline},"
                f"Shadow=0,MarginV={marginv},Alignment=2")
    
    def start_subtitle_burn(self):
        """开始烧录字幕"""
        video_path = self.subtitle_video_path.get().strip()
        srt_path = self.subtitle_srt_path.get().strip()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showwarning("提示", "请选择有效的视频文件")
            return
        if not srt_path or not os.path.exists(srt_path):
            messagebox.showwarning("提示", "请选择有效的字幕文件")
            return
        if not self.downloader.ffmpeg_available:
            messagebox.showwarning("提示", "烧录字幕需要ffmpeg支持\n请运行: winget install ffmpeg")
            return
        
        self.burn_btn.config(state='disabled')
        self.burn_progress['value'] = 0
        self.burn_progress_var.set("准备中...")
        
        thread = threading.Thread(target=self._burn_task, args=(video_path, srt_path))
        thread.daemon = True
        thread.start()
    
    def _burn_task(self, video_path, srt_path):
        """字幕烧录任务"""
        try:
            def log(msg, tag="info"):
                self.root.after(0, lambda: self._burn_log(msg, tag))
            
            log("🔥 开始烧录字幕...", "info")
            
            # 创建输出目录
            subtitle_video_dir = os.path.join(self.downloader.script_dir, "downloads", "字幕视频")
            if not os.path.exists(subtitle_video_dir):
                os.makedirs(subtitle_video_dir)
            
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(subtitle_video_dir, f"{base_name}_硬字幕.mp4")
            
            # 处理重名
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(subtitle_video_dir, f"{base_name}_硬字幕_{counter}.mp4")
                counter += 1
            
            # Windows路径转义处理：ffmpeg的subtitles滤镜需要特殊处理路径
            # 将srt文件复制到临时目录使用简单文件名，避免路径问题
            temp_srt = os.path.join(tempfile.gettempdir(), "subtitle_temp.srt")
            shutil.copy2(srt_path, temp_srt)
            
            try:
                force_style = self._get_subtitle_force_style()
                
                # 构建ffmpeg命令
                # 使用subtitles滤镜烧录字幕
                srt_path_escaped = temp_srt.replace("\\", "/").replace(":", "\\:")
                
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-vf', f"subtitles='{srt_path_escaped}':force_style='{force_style}'",
                    '-c:a', 'copy',
                    '-y', output_path
                ]
                
                log(f"📁 视频文件：{os.path.basename(video_path)}", "info")
                log(f"📝 字幕文件：{os.path.basename(srt_path)}", "info")
                log(f"🎬 输出路径：{os.path.basename(output_path)}", "info")
                log("⏳ 正在烧录，请耐心等待...", "info")
                
                # 使用Popen获取进度
                process = subprocess.Popen(
                    cmd,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # 解析ffmpeg的duration获取总时长
                duration = 0
                for line in process.stderr:
                    if "Duration" in line:
                        time_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', line)
                        if time_match:
                            h, m, s = time_match.groups()
                            duration = int(h) * 3600 + int(m) * 60 + float(s)
                    
                    # 解析进度
                    if "time=" in line:
                        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                        if time_match and duration > 0:
                            h, m, s = time_match.groups()
                            current = int(h) * 3600 + int(m) * 60 + float(s)
                            percent = min(current / duration * 100, 99)
                            self.root.after(0, lambda p=percent: self.burn_progress.__setitem__('value', p))
                            self.root.after(0, lambda p=percent: self.burn_progress_var.set(f"烧录中 {p:.0f}%"))
                
                process.wait()
                
                if process.returncode == 0 and os.path.exists(output_path):
                    log("=" * 50, "success")
                    log("✅ 字幕烧录完成！", "success")
                    log(f"📂 输出文件：{output_path}", "success")
                    file_size = os.path.getsize(output_path) / (1024 * 1024)
                    log(f"📦 文件大小：{file_size:.1f} MB", "success")
                    log("=" * 50, "success")
                    self.root.after(0, lambda: self.burn_progress.__setitem__('value', 100))
                    self.root.after(0, lambda: self.burn_progress_var.set("✅ 烧录完成！"))
                    
                    # 记录到下载历史
                    try:
                        self.history_manager.add_record(
                            platform="字幕烧录",
                            title=f"{base_name}_硬字幕",
                            file_type="字幕视频",
                            file_path=output_path,
                            url=""
                        )
                    except:
                        pass
                else:
                    raise Exception("ffmpeg烧录失败，请检查视频和字幕文件格式")
            
            finally:
                # 清理临时srt文件
                if os.path.exists(temp_srt):
                    try:
                        os.remove(temp_srt)
                    except:
                        pass
        
        except Exception as e:
            self.root.after(0, lambda: self._burn_log(f"❌ 错误：{str(e)}", "error"))
            self.root.after(0, lambda: self.burn_progress_var.set("❌ 烧录失败"))
        
        finally:
            self.root.after(0, lambda: self.burn_btn.config(state='normal'))
    
    def convert_srt_to_ass(self):
        """SRT转ASS格式"""
        srt_path = self.subtitle_srt_path.get().strip()
        if not srt_path or not os.path.exists(srt_path):
            srt_path = filedialog.askopenfilename(
                title="选择SRT字幕文件",
                filetypes=[("SRT字幕", "*.srt")]
            )
            if not srt_path:
                return
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # SRT解析
            blocks = re.split(r'\n\s*\n', srt_content.strip())
            ass_lines = [
                "[Script Info]",
                "Title: Subtitle",
                "ScriptType: v4.00+",
                "PlayResX: 1920",
                "PlayResY: 1080",
                "WrapStyle: 0",
                "",
                "[V4+ Styles]",
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
                "Style: Default,Microsoft YaHei UI,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1",
                "",
                "[Events]",
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
            ]
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # 时间行
                    time_match = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
                    if time_match:
                        g = time_match.groups()
                        start = f"{int(g[0]):01d}:{int(g[1]):02d}:{int(g[2]):02d}.{g[3][:2]}"
                        end = f"{int(g[4]):01d}:{int(g[5]):02d}:{int(g[6]):02d}.{g[7][:2]}"
                        text = '\\N'.join(lines[2:]).replace('<i>', '{\\i1}').replace('</i>', '{\\i0}')
                        ass_lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
            
            # 保存ASS文件
            ass_path = os.path.splitext(srt_path)[0] + ".ass"
            with open(ass_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(ass_lines))
            
            messagebox.showinfo("转换完成", f"ASS字幕已保存：\n{ass_path}")
        
        except Exception as e:
            messagebox.showerror("转换失败", f"SRT转ASS失败：{str(e)}")
    
    def _burn_log(self, message, tag="info"):
        """烧录日志"""
        self.burn_log.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.burn_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.burn_log.insert(tk.END, message + "\n", tag)
        self.burn_log.see(tk.END)
        self.burn_log.config(state='disabled')
    
    def setup_history_tab(self):
        """设置下载历史标签页"""
        main_frame = ttk.Frame(self.history_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="📜 下载历史",
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        version_badge = tk.Label(
            title_frame,
            text="v4.9",
            font=("Consolas", 10, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary'],
            padx=8, pady=3,
            relief='solid', bd=1
        )
        version_badge.pack(side=tk.RIGHT)
        
        # ========== 统计信息卡片 ==========
        stats_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        stats_card.pack(fill=tk.X, pady=(0, 15))
        
        stats_label = tk.Label(stats_card, text="📊 统计信息",
                              font=("Microsoft YaHei UI", 11, "bold"),
                              foreground=self.COLORS['text_primary'],
                              bg=self.COLORS['bg_secondary'],
                              anchor='w')
        stats_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        stats_row = tk.Frame(stats_card, bg=self.COLORS['bg_secondary'])
        stats_row.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # 今日下载
        self.today_count_label = tk.Label(
            stats_row, text="今日下载: 0 个",
            font=("Microsoft YaHei UI", 11, "bold"),
            foreground=self.COLORS['success'],
            bg=self.COLORS['bg_secondary']
        )
        self.today_count_label.pack(side=tk.LEFT, padx=(0, 30))
        
        # 总下载
        self.total_count_label = tk.Label(
            stats_row, text="总下载: 0 个",
            font=("Microsoft YaHei UI", 11, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_secondary']
        )
        self.total_count_label.pack(side=tk.LEFT)
        
        # ========== 搜索和筛选区域 ==========
        search_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        search_card.pack(fill=tk.X, pady=(0, 15))
        
        search_label = tk.Label(search_card, text="🔍 搜索筛选",
                               font=("Microsoft YaHei UI", 11, "bold"),
                               foreground=self.COLORS['text_primary'],
                               bg=self.COLORS['bg_secondary'],
                               anchor='w')
        search_label.pack(fill=tk.X, padx=12, pady=(10, 8))
        
        search_row = tk.Frame(search_card, bg=self.COLORS['bg_secondary'])
        search_row.pack(fill=tk.X, padx=12, pady=(0, 10))
        
        # 搜索框
        tk.Label(search_row, text="标题搜索：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.history_search_var = tk.StringVar()
        self.history_search_entry = tk.Entry(
            search_row,
            textvariable=self.history_search_var,
            font=("Microsoft YaHei UI", 10),
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['text_primary'],
            relief='flat',
            width=20
        )
        self.history_search_entry.pack(side=tk.LEFT, padx=8)
        self.history_search_entry.bind('<KeyRelease>', lambda e: self.refresh_history_list())
        
        # 平台筛选
        tk.Label(search_row, text="平台筛选：",
                font=("Microsoft YaHei UI", 10),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(side=tk.LEFT, padx=(20, 0))
        
        self.history_platform_filter = tk.StringVar(value='全部')
        platform_combo = ttk.Combobox(
            search_row,
            textvariable=self.history_platform_filter,
            values=['全部', '抖音', '哔哩哔哩', '小红书', '快手'],
            state='readonly',
            width=12
        )
        platform_combo.pack(side=tk.LEFT, padx=8)
        platform_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_history_list())
        
        # 清空历史按钮
        ttk.Button(
            search_row,
            text="🗑️ 清空历史",
            command=self.clear_history
        ).pack(side=tk.RIGHT)
        
        # ========== 历史记录表格 ==========
        table_card = tk.Frame(main_frame, bg=self.COLORS['bg_secondary'], relief='flat')
        table_card.pack(fill=tk.BOTH, expand=True)
        
        table_label = tk.Label(table_card, text="📋 历史记录",
                             font=("Microsoft YaHei UI", 11, "bold"),
                             foreground=self.COLORS['text_primary'],
                             bg=self.COLORS['bg_secondary'],
                             anchor='w')
        table_label.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        # 表格
        table_frame = tk.Frame(table_card, bg=self.COLORS['bg_secondary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        
        # 创建Treeview表格
        columns = ('时间', '平台', '标题', '类型', '文件路径')
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # 设置列宽
        self.history_tree.heading('时间', text='时间')
        self.history_tree.heading('平台', text='平台')
        self.history_tree.heading('标题', text='标题')
        self.history_tree.heading('类型', text='类型')
        self.history_tree.heading('文件路径', text='文件路径')
        
        self.history_tree.column('时间', width=140, anchor='center')
        self.history_tree.column('平台', width=80, anchor='center')
        self.history_tree.column('标题', width=200, anchor='w')
        self.history_tree.column('类型', width=80, anchor='center')
        self.history_tree.column('文件路径', width=250, anchor='w')
        
        # 滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击打开文件夹
        self.history_tree.bind('<Double-Button-1>', self.on_history_double_click)
        
        # 创建右键菜单
        self.history_context_menu = tk.Menu(self.root, tearoff=0, bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'])
        self.history_context_menu.add_command(label="📂 打开文件所在文件夹", command=self.open_history_file_folder)
        self.history_context_menu.add_command(label="📄 打开文件", command=self.open_history_file)
        self.history_context_menu.add_command(label="🔗 复制链接", command=self.copy_history_url)
        self.history_context_menu.add_separator()
        self.history_context_menu.add_command(label="🗑️ 删除记录", command=self.delete_history_record)
        
        # 绑定右键菜单
        self.history_tree.bind('<Button-3>', self.show_history_context_menu)
        
        # 初始化历史记录列表
        self.refresh_history_list()
    
    def setup_audio_tool_tab(self):
        """设置音频工具标签页"""
        main_frame = ttk.Frame(self.audio_tool_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ========== 标题区域 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text="🎵 音频工具箱",
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(side=tk.LEFT)
        
        version_badge = tk.Label(
            title_frame,
            text="v4.9",
            font=("Consolas", 10, "bold"),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_primary'],
            padx=8, pady=3,
            relief='solid', bd=1
        )
        version_badge.pack(side=tk.RIGHT)
        
        # ========== 功能区容器（三个卡片） ==========
        # 使用PanedWindow让三个功能区并排显示
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # ---- 音频格式转换卡片 ----
        convert_card = tk.Frame(paned, bg=self.COLORS['bg_secondary'], relief='flat')
        paned.add(convert_card, weight=1)
        self._setup_convert_frame(convert_card)
        
        # ---- 音频裁剪卡片 ----
        trim_card = tk.Frame(paned, bg=self.COLORS['bg_secondary'], relief='flat')
        paned.add(trim_card, weight=1)
        self._setup_trim_frame(trim_card)
        
        # ---- 音频合并卡片 ----
        merge_card = tk.Frame(paned, bg=self.COLORS['bg_secondary'], relief='flat')
        paned.add(merge_card, weight=1)
        self._setup_merge_frame(merge_card)
    
    def _setup_convert_frame(self, parent):
        """设置音频格式转换功能区"""
        # 标题
        tk.Label(parent, text="🔄 音频格式转换",
                font=("Microsoft YaHei UI", 12, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(12, 8))
        
        # 说明
        tk.Label(parent, text="支持MP3/WAV/M4A/AAC/OGG/FLAC互转",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(0, 10))
        
        # 源文件选择
        file_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        file_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(file_frame, text="源文件：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.convert_file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.convert_file_path,
                 font=("Microsoft YaHei UI", 9), width=20).pack(fill=tk.X, pady=(3, 0))
        
        ttk.Button(file_frame, text="浏览...",
                  command=self._browse_convert_file).pack(pady=(3, 0))
        
        # 目标格式
        format_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        format_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(format_frame, text="目标格式：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.convert_format_var = tk.StringVar(value="mp3")
        format_combo = ttk.Combobox(format_frame, textvariable=self.convert_format_var,
                                    values=["mp3", "wav", "m4a", "aac", "ogg", "flac"],
                                    state='readonly', width=10)
        format_combo.pack(pady=(3, 0))
        
        # 比特率
        bitrate_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        bitrate_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(bitrate_frame, text="比特率：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.convert_bitrate_var = tk.StringVar(value="192k")
        bitrate_combo = ttk.Combobox(bitrate_frame, textvariable=self.convert_bitrate_var,
                                    values=["128k", "192k", "256k", "320k"],
                                    state='readonly', width=10)
        bitrate_combo.pack(pady=(3, 0))
        
        # 转换按钮
        ttk.Button(parent, text="🔄 开始转换",
                  command=self._start_convert,
                  style="Success.TButton").pack(pady=(10, 5))
        
        # 进度条
        self.convert_progress = ttk.Progressbar(parent, mode='determinate',
                                              style='Gradient.Horizontal.TProgressbar')
        self.convert_progress.pack(fill=tk.X, padx=12, pady=5)
        
        # 日志
        self.convert_log = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, font=("JetBrains Mono", 8),
            relief=tk.FLAT, bg=self.COLORS['log_bg'], fg="#00ff88",
            insertbackground=self.COLORS['text_primary'],
            padx=5, pady=5, height=6, state='disabled'
        )
        self.convert_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(5, 12))
        self.convert_log.tag_configure("info", foreground="#00ff88")
        self.convert_log.tag_configure("warning", foreground=self.COLORS['warning'])
        self.convert_log.tag_configure("error", foreground=self.COLORS['error'])
        self.convert_log.tag_configure("success", foreground="#69f0ae")
    
    def _setup_trim_frame(self, parent):
        """设置音频裁剪功能区"""
        # 标题
        tk.Label(parent, text="✂️ 音频裁剪",
                font=("Microsoft YaHei UI", 12, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(12, 8))
        
        # 说明
        tk.Label(parent, text="截取音频片段，格式：MM:SS 或 HH:MM:SS",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(0, 10))
        
        # 源文件选择
        file_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        file_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(file_frame, text="音频文件：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.trim_file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.trim_file_path,
                 font=("Microsoft YaHei UI", 9), width=20).pack(fill=tk.X, pady=(3, 0))
        
        ttk.Button(file_frame, text="浏览...",
                  command=self._browse_trim_file).pack(pady=(3, 0))
        
        # 开始时间
        start_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        start_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(start_frame, text="开始时间：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.trim_start_var = tk.StringVar(value="00:00")
        ttk.Entry(start_frame, textvariable=self.trim_start_var,
                 font=("Microsoft YaHei UI", 9), width=15).pack(pady=(3, 0))
        
        # 结束时间
        end_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        end_frame.pack(fill=tk.X, padx=12, pady=5)
        
        tk.Label(end_frame, text="结束时间：",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w')
        
        self.trim_end_var = tk.StringVar(value="00:00")
        ttk.Entry(end_frame, textvariable=self.trim_end_var,
                 font=("Microsoft YaHei UI", 9), width=15).pack(pady=(3, 0))
        
        # 时长预览
        self.trim_preview_label = tk.Label(
            parent, text="时长: --",
            font=("Microsoft YaHei UI", 9),
            foreground=self.COLORS['accent'],
            bg=self.COLORS['bg_secondary']
        )
        self.trim_preview_label.pack(pady=5)
        
        # 裁剪按钮
        ttk.Button(parent, text="✂️ 开始裁剪",
                  command=self._start_trim,
                  style="Success.TButton").pack(pady=(5, 5))
        
        # 进度条
        self.trim_progress = ttk.Progressbar(parent, mode='determinate',
                                             style='Gradient.Horizontal.TProgressbar')
        self.trim_progress.pack(fill=tk.X, padx=12, pady=5)
        
        # 日志
        self.trim_log = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, font=("JetBrains Mono", 8),
            relief=tk.FLAT, bg=self.COLORS['log_bg'], fg="#00ff88",
            insertbackground=self.COLORS['text_primary'],
            padx=5, pady=5, height=6, state='disabled'
        )
        self.trim_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(5, 12))
        self.trim_log.tag_configure("info", foreground="#00ff88")
        self.trim_log.tag_configure("warning", foreground=self.COLORS['warning'])
        self.trim_log.tag_configure("error", foreground=self.COLORS['error'])
        self.trim_log.tag_configure("success", foreground="#69f0ae")
    
    def _setup_merge_frame(self, parent):
        """设置音频合并功能区"""
        # 标题
        tk.Label(parent, text="🔗 音频合并",
                font=("Microsoft YaHei UI", 12, "bold"),
                foreground=self.COLORS['text_primary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(12, 8))
        
        # 说明
        tk.Label(parent, text="多音频文件合并为一个",
                font=("Microsoft YaHei UI", 9),
                foreground=self.COLORS['text_secondary'],
                bg=self.COLORS['bg_secondary']).pack(anchor='w', padx=12, pady=(0, 10))
        
        # 添加文件按钮
        btn_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        btn_frame.pack(fill=tk.X, padx=12, pady=5)
        
        ttk.Button(btn_frame, text="➕ 添加音频文件",
                  command=self._add_merge_files).pack(side=tk.LEFT)
        
        ttk.Button(btn_frame, text="🗑️ 清空",
                  command=self._clear_merge_files).pack(side=tk.LEFT, padx=5)
        
        # 文件列表（Listbox）
        list_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)
        
        self.merge_listbox = tk.Listbox(
            list_frame, font=("Microsoft YaHei UI", 9),
            bg=self.COLORS['bg_tertiary'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground="#ffffff",
            relief='flat', height=6
        )
        self.merge_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 文件列表滚动条
        merge_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.merge_listbox.yview)
        self.merge_listbox.configure(yscrollcommand=merge_scroll.set)
        merge_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 顺序调整按钮
        order_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'])
        order_frame.pack(fill=tk.X, padx=12, pady=5)
        
        ttk.Button(order_frame, text="⬆️ 上移",
                  command=lambda: self._move_merge_item(-1)).pack(side=tk.LEFT)
        ttk.Button(order_frame, text="⬇️ 下移",
                  command=lambda: self._move_merge_item(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame, text="❌ 删除",
                  command=self._remove_merge_item).pack(side=tk.LEFT)
        
        # 合并按钮
        ttk.Button(parent, text="🔗 开始合并",
                  command=self._start_merge,
                  style="Success.TButton").pack(pady=(5, 5))
        
        # 进度条
        self.merge_progress = ttk.Progressbar(parent, mode='determinate',
                                             style='Gradient.Horizontal.TProgressbar')
        self.merge_progress.pack(fill=tk.X, padx=12, pady=5)
        
        # 日志
        self.merge_log = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, font=("JetBrains Mono", 8),
            relief=tk.FLAT, bg=self.COLORS['log_bg'], fg="#00ff88",
            insertbackground=self.COLORS['text_primary'],
            padx=5, pady=5, height=6, state='disabled'
        )
        self.merge_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(5, 12))
        self.merge_log.tag_configure("info", foreground="#00ff88")
        self.merge_log.tag_configure("warning", foreground=self.COLORS['warning'])
        self.merge_log.tag_configure("error", foreground=self.COLORS['error'])
        self.merge_log.tag_configure("success", foreground="#69f0ae")
        
        # 合并文件列表
        self.merge_files = []
    
    def _browse_convert_file(self):
        """浏览选择要转换的音频文件"""
        file_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.convert_file_path.set(file_path)
    
    def _browse_trim_file(self):
        """浏览选择要裁剪的音频文件"""
        file_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.trim_file_path.set(file_path)
            self._update_trim_preview()
    
    def _update_trim_preview(self):
        """更新裁剪时长预览"""
        try:
            start_str = self.trim_start_var.get().strip()
            end_str = self.trim_end_var.get().strip()
            
            start_sec = self._parse_time_to_seconds(start_str)
            end_sec = self._parse_time_to_seconds(end_str)
            
            if start_sec is not None and end_sec is not None and end_sec > start_sec:
                duration = end_sec - start_sec
                self.trim_preview_label.config(text=f"裁剪时长: {duration:.1f} 秒")
            else:
                self.trim_preview_label.config(text="时长: --")
        except:
            self.trim_preview_label.config(text="时长: --")
    
    def _parse_time_to_seconds(self, time_str):
        """解析时间字符串为秒数，支持 MM:SS 和 HH:MM:SS 格式"""
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            elif len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
        except:
            pass
        return None
    
    def _convert_log(self, message, tag="info"):
        """格式转换日志"""
        self.convert_log.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.convert_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.convert_log.insert(tk.END, message + "\n", tag)
        self.convert_log.see(tk.END)
        self.convert_log.config(state='disabled')
    
    def _trim_log(self, message, tag="info"):
        """音频裁剪日志"""
        self.trim_log.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.trim_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.trim_log.insert(tk.END, message + "\n", tag)
        self.trim_log.see(tk.END)
        self.trim_log.config(state='disabled')
    
    def _merge_log(self, message, tag="info"):
        """音频合并日志"""
        self.merge_log.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.merge_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.merge_log.insert(tk.END, message + "\n", tag)
        self.merge_log.see(tk.END)
        self.merge_log.config(state='disabled')
    
    def _start_convert(self):
        """开始音频格式转换"""
        if not self.downloader.ffmpeg_available:
            messagebox.showwarning("提示", "音频转换需要ffmpeg支持\n请运行: winget install ffmpeg")
            return
        
        file_path = self.convert_file_path.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("提示", "请选择有效的音频文件")
            return
        
        target_format = self.convert_format_var.get()
        bitrate = self.convert_bitrate_var.get()
        
        self.convert_progress['value'] = 0
        self._convert_log("开始转换...", "info")
        
        thread = threading.Thread(target=self._convert_task, args=(file_path, target_format, bitrate))
        thread.daemon = True
        thread.start()
    
    def _convert_task(self, file_path, target_format, bitrate):
        """格式转换任务"""
        try:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(self.downloader.audio_convert_dir, f"{base_name}_converted.{target_format}")
            
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(self.downloader.audio_convert_dir, f"{base_name}_converted_{counter}.{target_format}")
                counter += 1
            
            self._convert_log(f"源文件: {os.path.basename(file_path)}", "info")
            self._convert_log(f"目标格式: {target_format.upper()}", "info")
            self._convert_log(f"比特率: {bitrate}", "info")
            
            # 根据格式选择编码器
            codec_map = {
                'mp3': 'libmp3lame',
                'wav': 'pcm_s16le',
                'm4a': 'aac',
                'aac': 'aac',
                'ogg': 'libvorbis',
                'flac': 'flac'
            }
            codec = codec_map.get(target_format, 'copy')
            
            cmd = ['ffmpeg', '-i', file_path]
            if target_format != 'wav':
                cmd.extend(['-acodec', codec, '-b:a', bitrate])
            else:
                cmd.extend(['-acodec', codec])
            cmd.extend(['-y', output_path])
            
            self._convert_log("正在转换，请稍候...", "info")
            
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            
            # 解析进度
            duration = 0
            for line in process.stderr:
                if "Duration" in line:
                    time_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', line)
                    if time_match:
                        h, m, s = time_match.groups()
                        duration = int(h) * 3600 + int(m) * 60 + float(s)
                if "time=" in line and duration > 0:
                    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                    if time_match:
                        h, m, s = time_match.groups()
                        current = int(h) * 3600 + int(m) * 60 + float(s)
                        percent = min(current / duration * 100, 99)
                        self.root.after(0, lambda p=percent: self.convert_progress.__setitem__('value', p))
            
            process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                self._convert_log("=" * 30, "success")
                self._convert_log("✅ 转换完成！", "success")
                self._convert_log(f"📁 {os.path.basename(output_path)}", "success")
                self._convert_log(f"📦 {file_size:.1f} MB", "success")
                self._convert_log("=" * 30, "success")
                self.root.after(0, lambda: self.convert_progress.__setitem__('value', 100))
                
                # 记录到历史
                self.root.after(0, lambda: self.add_to_history("音频转换", base_name, "音频", output_path, ""))
            else:
                raise Exception("转换失败")
        
        except Exception as e:
            self._convert_log(f"❌ 错误: {str(e)}", "error")
        
        finally:
            pass
    
    def _start_trim(self):
        """开始音频裁剪"""
        if not self.downloader.ffmpeg_available:
            messagebox.showwarning("提示", "音频裁剪需要ffmpeg支持\n请运行: winget install ffmpeg")
            return
        
        file_path = self.trim_file_path.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("提示", "请选择有效的音频文件")
            return
        
        start_str = self.trim_start_var.get().strip()
        end_str = self.trim_end_var.get().strip()
        
        start_sec = self._parse_time_to_seconds(start_str)
        end_sec = self._parse_time_to_seconds(end_str)
        
        if start_sec is None or end_sec is None:
            messagebox.showwarning("提示", "时间格式不正确，请使用 MM:SS 或 HH:MM:SS 格式")
            return
        
        if end_sec <= start_sec:
            messagebox.showwarning("提示", "结束时间必须大于开始时间")
            return
        
        self.trim_progress['value'] = 0
        self._trim_log("开始裁剪...", "info")
        
        thread = threading.Thread(target=self._trim_task, args=(file_path, start_sec, end_sec))
        thread.daemon = True
        thread.start()
    
    def _trim_task(self, file_path, start_sec, end_sec):
        """音频裁剪任务"""
        try:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1]
            output_path = os.path.join(self.downloader.audio_convert_dir, f"{base_name}_trimmed{ext}")
            
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(self.downloader.audio_convert_dir, f"{base_name}_trimmed_{counter}{ext}")
                counter += 1
            
            self._trim_log(f"源文件: {os.path.basename(file_path)}", "info")
            self._trim_log(f"裁剪范围: {start_sec:.1f}s ~ {end_sec:.1f}s", "info")
            self._trim_log("正在处理...", "info")
            
            # ffmpeg裁剪命令
            cmd = [
                'ffmpeg', '-i', file_path,
                '-ss', str(start_sec),
                '-to', str(end_sec),
                '-c', 'copy',
                '-y', output_path
            ]
            
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                duration = end_sec - start_sec
                self._trim_log("=" * 30, "success")
                self._trim_log("✅ 裁剪完成！", "success")
                self._trim_log(f"📁 {os.path.basename(output_path)}", "success")
                self._trim_log(f"⏱️ 时长: {duration:.1f}s", "success")
                self._trim_log(f"📦 {file_size:.1f} MB", "success")
                self._trim_log("=" * 30, "success")
                self.root.after(0, lambda: self.trim_progress.__setitem__('value', 100))
                
                # 记录到历史
                self.root.after(0, lambda: self.add_to_history("音频裁剪", base_name, "音频", output_path, ""))
            else:
                raise Exception("裁剪失败")
        
        except Exception as e:
            self._trim_log(f"❌ 错误: {str(e)}", "error")
    
    def _add_merge_files(self):
        """添加要合并的音频文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择音频文件（可多选）",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"),
                ("所有文件", "*.*")
            ]
        )
        if file_paths:
            for fp in file_paths:
                if fp not in self.merge_files:
                    self.merge_files.append(fp)
                    self.merge_listbox.insert(tk.END, os.path.basename(fp))
            self._merge_log(f"已添加 {len(file_paths)} 个文件", "info")
    
    def _clear_merge_files(self):
        """清空合并文件列表"""
        self.merge_files.clear()
        self.merge_listbox.delete(0, tk.END)
        self._merge_log("文件列表已清空", "info")
    
    def _remove_merge_item(self):
        """删除选中的合并项"""
        selection = self.merge_listbox.curselection()
        if selection:
            idx = selection[0]
            self.merge_listbox.delete(idx)
            del self.merge_files[idx]
    
    def _move_merge_item(self, direction):
        """移动合并列表中的项"""
        selection = self.merge_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        new_idx = idx + direction
        
        if 0 <= new_idx < self.merge_listbox.size():
            # 交换列表中的项
            self.merge_files[idx], self.merge_files[new_idx] = self.merge_files[new_idx], self.merge_files[idx]
            
            # 更新Listbox显示
            self.merge_listbox.delete(idx)
            self.merge_listbox.insert(new_idx, os.path.basename(self.merge_files[new_idx]))
            self.merge_listbox.selection_set(new_idx)
    
    def _start_merge(self):
        """开始音频合并"""
        if not self.downloader.ffmpeg_available:
            messagebox.showwarning("提示", "音频合并需要ffmpeg支持\n请运行: winget install ffmpeg")
            return
        
        if len(self.merge_files) < 2:
            messagebox.showwarning("提示", "请至少添加2个音频文件进行合并")
            return
        
        self.merge_progress['value'] = 0
        self._merge_log("开始合并...", "info")
        
        thread = threading.Thread(target=self._merge_task)
        thread.daemon = True
        thread.start()
    
    def _merge_task(self):
        """音频合并任务"""
        try:
            # 创建临时文件列表
            temp_list_file = os.path.join(tempfile.gettempdir(), "audio_merge_list.txt")
            
            with open(temp_list_file, 'w', encoding='utf-8') as f:
                for file_path in self.merge_files:
                    # ffmpeg需要Windows路径转义
                    escaped_path = file_path.replace("\\", "/").replace(":", "\\:")
                    f.write(f"file '{escaped_path}'\n")
            
            self._merge_log(f"共 {len(self.merge_files)} 个文件", "info")
            
            # 生成输出文件名
            output_path = os.path.join(self.downloader.audio_convert_dir, "merged_audio.mp3")
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(self.downloader.audio_convert_dir, f"merged_audio_{counter}.mp3")
                counter += 1
            
            self._merge_log("正在合并...", "info")
            
            # ffmpeg合并命令
            cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', temp_list_file, '-c', 'copy', '-y', output_path]
            
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            
            # 简单等待
            process.wait()
            
            # 清理临时文件
            if os.path.exists(temp_list_file):
                try:
                    os.remove(temp_list_file)
                except:
                    pass
            
            if process.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                self._merge_log("=" * 30, "success")
                self._merge_log("✅ 合并完成！", "success")
                self._merge_log(f"📁 {os.path.basename(output_path)}", "success")
                self._merge_log(f"📦 {file_size:.1f} MB", "success")
                self._merge_log("=" * 30, "success")
                self.root.after(0, lambda: self.merge_progress.__setitem__('value', 100))
                
                # 记录到历史
                self.root.after(0, lambda: self.add_to_history("音频合并", "merged_audio", "音频", output_path, ""))
            else:
                raise Exception("合并失败")
        
        except Exception as e:
            self._merge_log(f"❌ 错误: {str(e)}", "error")
    
    def refresh_history_list(self):
        """刷新历史记录列表"""
        # 清空现有记录
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # 获取筛选条件
        keyword = self.history_search_var.get()
        platform = self.history_platform_filter.get()
        
        # 搜索历史
        records = self.history_manager.search(keyword, platform)
        
        # 按时间倒序插入
        for record in records:
            # 截断标题和路径显示
            title = record['title'][:30] + '...' if len(record['title']) > 30 else record['title']
            file_path = record['file_path']
            if len(file_path) > 40:
                file_path = '...' + file_path[-37:]
            
            self.history_tree.insert('', tk.END, values=(
                record['time'],
                record['platform'],
                title,
                record['file_type'],
                file_path
            ), tags=(record['id'],))  # 用id作为tag方便查找
        
        # 更新统计信息
        stats = self.history_manager.get_stats()
        self.today_count_label.config(text=f"今日下载: {stats['today']} 个")
        self.total_count_label.config(text=f"总下载: {stats['total']} 个")
    
    def add_to_history(self, platform, title, file_type, file_path, url):
        """添加下载记录到历史"""
        self.history_manager.add_record(platform, title, file_type, file_path, url)
        self.refresh_history_list()
    
    def clear_history(self):
        """清空历史记录"""
        result = messagebox.askyesno(
            "确认清空",
            "确定要清空所有下载历史记录吗？\n（不会删除实际文件）",
            icon='question'
        )
        if result:
            self.history_manager.clear_all()
            self.refresh_history_list()
            self.log("📜 下载历史已清空", "info")
    
    def on_history_double_click(self, event):
        """双击历史记录，打开文件所在文件夹"""
        # 获取点击的项
        selection = self.history_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.history_tree.item(item, 'values')
        if not values:
            return
        
        # 查找对应的记录
        keyword = self.history_search_var.get()
        platform = self.history_platform_filter.get()
        records = self.history_manager.search(keyword, platform)
        
        # 根据行号找到对应记录
        children = self.history_tree.get_children()
        row_index = children.index(item) if item in children else -1
        if row_index >= 0 and row_index < len(records):
            record = records[row_index]
            file_path = record['file_path']
            
            if os.path.exists(file_path):
                folder = os.path.dirname(file_path)
                try:
                    if os.name == 'nt':
                        os.startfile(folder)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', folder])
                    else:
                        subprocess.run(['xdg-open', folder])
                except Exception as e:
                    self.log(f"❌ 无法打开文件夹：{str(e)}", "error")
            else:
                self.log(f"⚠️ 文件不存在：{file_path}", "warning")
    
    def show_history_context_menu(self, event):
        """显示历史记录右键菜单"""
        # 选中右键点击的行
        item = self.history_tree.identify_row(event.y)
        if item:
            self.history_tree.selection_set(item)
            self.history_context_menu.post(event.x_root, event.y_root)
    
    def _get_selected_history_record(self):
        """获取选中的历史记录"""
        selection = self.history_tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        children = self.history_tree.get_children()
        row_index = children.index(item) if item in children else -1
        
        if row_index >= 0:
            keyword = self.history_search_var.get()
            platform = self.history_platform_filter.get()
            records = self.history_manager.search(keyword, platform)
            if row_index < len(records):
                return records[row_index]
        
        return None
    
    def open_history_file_folder(self):
        """打开历史文件所在文件夹"""
        record = self._get_selected_history_record()
        if not record:
            return
        
        file_path = record['file_path']
        if os.path.exists(file_path):
            folder = os.path.dirname(file_path)
            try:
                if os.name == 'nt':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', folder])
                else:
                    subprocess.run(['xdg-open', folder])
            except Exception as e:
                self.log(f"❌ 无法打开文件夹：{str(e)}", "error")
        else:
            self.log(f"⚠️ 文件不存在：{file_path}", "warning")
    
    def open_history_file(self):
        """打开历史文件"""
        record = self._get_selected_history_record()
        if not record:
            return
        
        file_path = record['file_path']
        if os.path.exists(file_path):
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', file_path])
                else:
                    subprocess.run(['xdg-open', file_path])
            except Exception as e:
                self.log(f"❌ 无法打开文件：{str(e)}", "error")
        else:
            self.log(f"⚠️ 文件不存在：{file_path}", "warning")
    
    def copy_history_url(self):
        """复制历史记录链接"""
        record = self._get_selected_history_record()
        if not record:
            return
        
        try:
            pyperclip.copy(record['url'])
            self.log(f"🔗 已复制链接：{record['url'][:50]}...", "info")
        except:
            self.log("❌ 复制链接失败", "error")
    
    def delete_history_record(self):
        """删除历史记录"""
        record = self._get_selected_history_record()
        if not record:
            return
        
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除这条历史记录吗？\n（不会删除实际文件）",
            icon='question'
        )
        if result:
            self.history_manager.delete_record(record['id'])
            self.refresh_history_list()
            self.log(f"🗑️ 已删除记录：{record['title'][:30]}...", "info")
    
    def _on_batch_text_focus_in(self, event):
        """文本框获得焦点时清空占位符"""
        content = self.batch_text.get(1.0, tk.END).strip()
        placeholder = "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx"
        if content == placeholder:
            self.batch_text.delete(1.0, tk.END)
    
    def _on_batch_text_focus_out(self, event):
        """文本框失去焦点时恢复占位符"""
        content = self.batch_text.get(1.0, tk.END).strip()
        if not content:
            placeholder = "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx"
            self.batch_text.insert(1.0, placeholder)
    
    def clear_batch_input(self):
        """清空批量下载输入"""
        placeholder = "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx"
        self.batch_text.delete(1.0, tk.END)
        self.batch_text.insert(1.0, placeholder)
        
        # 清空表格
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        
        self.batch_summary_label.config(text="", fg=self.COLORS['text_primary'])
        self.batch_progress_label.config(text="")
    
    def parse_batch_urls(self, text):
        """解析批量输入文本，提取所有链接"""
        urls = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试提取链接
            url = self.downloader.extract_url(line)
            if url and url not in urls:
                urls.append(url)
        
        return urls
    
    def start_batch_download(self):
        """开始批量下载"""
        if self.batch_running:
            return
        
        # 获取输入内容
        input_text = self.batch_text.get(1.0, tk.END).strip()
        placeholder = "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx"
        if input_text == placeholder:
            input_text = ""
        
        if not input_text:
            messagebox.showwarning("提示", "请输入视频链接")
            return
        
        # 解析链接
        self.batch_urls = self.parse_batch_urls(input_text)
        
        if not self.batch_urls:
            messagebox.showwarning("提示", "未检测到有效链接，请检查输入格式")
            return
        
        # 清空之前的表格
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        
        # 清空结果
        self.batch_results = []
        
        # 插入初始行
        for i, url in enumerate(self.batch_urls, 1):
            platform = self.downloader.detect_platform(url)
            short_url = url[:50] + "..." if len(url) > 50 else url
            self.batch_tree.insert('', tk.END, values=(i, short_url, platform, "等待中", ""))
        
        # 更新UI状态
        self.batch_running = True
        self.batch_stop_flag = False
        self.batch_start_btn.config(state='disabled')
        self.batch_stop_btn.config(state='normal')
        
        # 启动下载线程
        thread = threading.Thread(target=self._batch_download_task)
        thread.daemon = True
        thread.start()
    
    def _batch_download_task(self):
        """批量下载任务（在线程中运行）"""
        total = len(self.batch_urls)
        success_count = 0
        fail_count = 0
        
        self.root.after(0, lambda: self.batch_progress_label.config(
            text=f"进度: 0/{total}",
            fg=self.COLORS['text_primary']
        ))
        
        for i, url in enumerate(self.batch_urls):
            if self.batch_stop_flag:
                self.root.after(0, lambda idx=i, rid=None: self._update_batch_row(i, "已停止", ""))
                continue
            
            # 获取对应的行
            row_id = self.batch_tree.get_children()[i] if i < len(self.batch_tree.get_children()) else None
            
            try:
                # 更新状态为下载中
                self.root.after(0, lambda idx=i, rid=None: self._update_batch_row(idx, "下载中...", ""))
                self.root.after(0, lambda idx=i: self.batch_progress_label.config(
                    text=f"进度: {idx + 1}/{total}",
                    fg=self.COLORS['accent']
                ))
                
                # 统一4参数回调
                def make_progress_callback(idx):
                    def callback(percent, downloaded, total_size, message):
                        if not self.batch_stop_flag:
                            self.root.after(0, lambda: self.batch_progress_label.config(
                                text=f"进度: {idx + 1}/{total} - {message}",
                                fg=self.COLORS['accent']
                            ))
                    return callback
                
                platform = self.downloader.detect_platform(url)
                
                # 下载视频
                video_result = self.downloader.download_video(url, make_progress_callback(i))
                video_filename = os.path.basename(video_result.get('file_path', '')) if video_result.get('file_path') else ""
                
                # 添加到历史记录
                if video_result.get('file_path') and os.path.exists(video_result['file_path']):
                    self.root.after(0, lambda p=platform, t=video_result.get('title', '视频'), fp=video_result['file_path'], u=url: 
                                  self.add_to_history(p, t, '视频', fp, u))
                    self.root.after(0, lambda fn=video_filename: self.log(f"✅ 视频下载完成 → {fn}", "success"))
                else:
                    self.root.after(0, lambda: self.log(f"📹 视频下载完成", "success"))
                
                # 提取音频
                audio_filename = ""
                if self.downloader.ffmpeg_available:
                    self.root.after(0, lambda: self.log("🎵 正在提取音频..."))
                    
                    audio_result = self.downloader.download_audio(
                        url,
                        make_progress_callback(i)
                    )
                    
                    if audio_result.get('file_path') and os.path.exists(audio_result['file_path']):
                        audio_filename = os.path.basename(audio_result['file_path'])
                        # 添加音频到历史记录
                        self.root.after(0, lambda p=platform, t=audio_result.get('title', '音频'), fp=audio_result['file_path'], u=url:
                                      self.add_to_history(p, t, '音频', fp, u))
                        self.root.after(0, lambda af=audio_filename: self.log(f"🎵 音频提取完成 → {af}", "success"))
                    else:
                        self.root.after(0, lambda: self.log("🎵 音频提取完成", "success"))
                else:
                    self.root.after(0, lambda: self.log("⚠️ 跳过音频提取（ffmpeg不可用）", "warning"))
                
                # 更新行状态为成功
                final_filename = video_filename if video_filename else audio_filename
                self.root.after(0, lambda idx=i, rid=None: self._update_batch_row(idx, "✅ 成功", final_filename))
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda idx=i, rid=None, err=error_msg: self._update_batch_row(idx, "❌ 失败", err[:30]))
                self.root.after(0, lambda err=error_msg: self.log(f"❌ 下载失败：{err[:80]}", "error"))
                fail_count += 1
            
            # 更新进度
            self.root.after(0, lambda idx=i: self.batch_progress_label.config(
                text=f"进度: {idx + 1}/{total}",
                fg=self.COLORS['success'] if idx == total - 1 else self.COLORS['accent']
            ))
        
        # 批量下载完成
        self.batch_running = False
        self.batch_start_btn.config(state='normal')
        self.batch_stop_btn.config(state='disabled')
        
        # 更新汇总
        self.root.after(0, lambda: self.batch_summary_label.config(
            text=f"📊 汇总：成功 {success_count} 个，失败 {fail_count} 个",
            fg=self.COLORS['success'] if fail_count == 0 else self.COLORS['warning']
        ))
        
        self.root.after(0, lambda: self.log(f"📦 批量下载完成！成功 {success_count} 个，失败 {fail_count} 个", 
                                            "success" if fail_count == 0 else "warning"))
    
    def _update_batch_row(self, index, status, filename):
        """更新表格行"""
        try:
            children = self.batch_tree.get_children()
            if index < len(children):
                row_id = children[index]
                current_values = list(self.batch_tree.item(row_id, 'values'))
                current_values[3] = status
                current_values[4] = filename
                self.batch_tree.item(row_id, values=current_values)
        except Exception:
            pass
    
    def stop_batch_download(self):
        """停止批量下载"""
        if self.batch_running:
            self.batch_stop_flag = True
            self.batch_progress_label.config(text="正在停止...", fg=self.COLORS['warning'])
            self.batch_stop_btn.config(state='disabled')
    
    def browse_asr_file(self):
        """浏览选择音频/视频文件"""
        filetypes = [
            ("音频文件", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"),
            ("视频文件", "*.mp4 *.avi *.mkv *.mov"),
            ("所有文件", "*.*")
        ]
        file_path = filedialog.askopenfilename(
            title="选择音频或视频文件",
            filetypes=filetypes
        )
        if file_path:
            self.asr_file_path.set(file_path)
    
    def start_asr_task(self):
        """启动ASR转写任务"""
        if self.asr_task_running:
            return
        
        file_path = self.asr_file_path.get().strip()
        link = self.asr_link.get().strip()
        
        # 检查设备选择（实时检测CUDA，不用缓存值）
        device = self.asr_device_var.get()
        if device == 'gpu':
            cuda_now = ASREngine.check_cuda_available()
            if not cuda_now:
                messagebox.showwarning(
                    "CUDA不可用",
                    "未检测到CUDA支持。\n\n"
                    "如果您想使用GPU加速，请：\n"
                    "1. 确保已安装NVIDIA显卡驱动\n"
                    "2. pip install nvidia-cublas-cu12 nvidia-cudnn-cu12\n"
                    "3. 重启程序\n\n"
                    "程序将使用CPU模式继续运行。"
                )
                device = 'cpu'
            else:
                # 更新缓存
                self.cuda_available = True
        
        # 自动从分享文本中提取链接
        if link and not link.startswith('http'):
            import re as _re
            url_match = _re.search(r'https?://[^\s<>"\']+', link)
            if url_match:
                link = url_match.group(0)
        
        if not file_path and not link:
            messagebox.showwarning("提示", "请选择文件或输入视频链接")
            return
        
        self.asr_task_running = True
        self.asr_start_btn.config(state='disabled')
        self.asr_progress_var.set("准备中...")
        self.asr_progress['value'] = 0
        self.asr_result.config(state='normal')
        self.asr_result.delete(1.0, tk.END)
        self.asr_result.config(state='disabled')
        
        thread = threading.Thread(target=self._asr_task, args=(file_path, link, device))
        thread.daemon = True
        thread.start()
    
    def _asr_task(self, file_path, link, device):
        """ASR转写任务（在线程中运行）"""
        temp_dir = None  # 记录临时目录
        task_url = link  # 记录任务使用的链接
        task_platform = self.downloader.detect_platform(link) if link else '未知平台'
        try:
            model_size = self.asr_model_var.get()
            language = self.asr_lang_var.get()
            
            def progress_callback(percent, message):
                self.root.after(0, lambda p=percent, m=message: self._update_asr_progress(p, m))
            
            def log_callback(message, tag="info"):
                self.root.after(0, lambda m=message, t=tag: self._asr_log(m, t))
            
            progress_callback(0, "正在处理...")
            device_desc = "GPU" if device == "gpu" else ("CPU" if device == "cpu" else "Auto")
            log_callback(f"开始语音识别... (设备: {device_desc}, 模型: {model_size})", "info")
            
            audio_result = None
            if link:
                # 从链接只下载音频流（不下载视频，节省存储）
                log_callback(f"📥 正在提取音频：{link[:50]}...", "info")
                
                audio_result = self.downloader.download_audio_only(
                    link,
                    progress_callback=lambda p, d, t, msg: self.root.after(0, lambda m=f"   {msg} ({p:.1f}%)": self._asr_log(m, "info"))
                )
                
                if audio_result.get('file_path') and os.path.exists(audio_result['file_path']):
                    file_path = audio_result['file_path']
                    temp_dir = audio_result.get('temp_dir')
                    log_callback(f"✅ 音频提取完成：{os.path.basename(file_path)}", "success")
                else:
                    raise Exception("音频提取失败")
            
            if not file_path or not os.path.exists(file_path):
                raise Exception(f"文件不存在：{file_path}")
            
            log_callback(f"🎤 开始识别：{os.path.basename(file_path)}", "info")
            
            # 执行转写，传入device参数
            result = self.downloader.transcribe_file(
                file_path,
                model_size=model_size,
                progress_callback=progress_callback,
                language=language,
                device=device
            )
            
            if result['success']:
                log_callback("=" * 50, "success")
                log_callback(f"✅ 识别完成！", "success")
                log_callback(f"📄 语言：{result['language']} (概率: {result['language_prob']:.1%})", "success")
                log_callback(f"⏱️ 时长：{result['duration']:.1f} 秒", "success")
                
                # 如果是通过链接下载的，需要移动txt和srt文件到文字稿目录
                title = audio_result['title'] if audio_result else os.path.splitext(os.path.basename(file_path))[0]
                
                if link and temp_dir:
                    # Bug修复：移动txt和srt文件到文字稿目录
                    txt_path = result.get('txt_path', '')
                    srt_path = result.get('srt_path', '')
                    
                    if txt_path and os.path.exists(txt_path):
                        try:
                            moved_paths = self.downloader.move_asr_files_to_text_dir(
                                txt_path, srt_path, title
                            )
                            result['txt_path'] = moved_paths['txt_path']
                            result['srt_path'] = moved_paths['srt_path']
                            log_callback(f"📂 文字稿已保存到：{self.downloader.text_dir}", "success")
                        except Exception as e:
                            log_callback(f"⚠️ 移动文件失败: {str(e)}", "warning")
                
                log_callback(f"📝 文字稿：{os.path.basename(result['txt_path'])}", "success")
                log_callback(f"📝 字幕：{os.path.basename(result['srt_path'])}", "success")
                log_callback("=" * 50, "success")
                
                # 添加到历史记录 - 文字稿
                txt_file_path = result.get('txt_path', '')
                if txt_file_path and os.path.exists(txt_file_path):
                    self.root.after(0, lambda p=task_platform, t=title, fp=txt_file_path, u=task_url:
                                  self.add_to_history(p, t, '文字稿', fp, u))
                
                # 如果是通过链接下载的临时音频，识别完后自动清理
                if link and file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        # 尝试清理临时目录
                        if temp_dir and temp_dir.startswith(tempfile.gettempdir()):
                            try:
                                # 先删除可能残留的其他文件
                                if os.path.exists(temp_dir):
                                    for f in os.listdir(temp_dir):
                                        try:
                                            os.remove(os.path.join(temp_dir, f))
                                        except:
                                            pass
                                    if not os.listdir(temp_dir):
                                        os.rmdir(temp_dir)
                            except:
                                pass
                        log_callback("🗑️ 临时文件已自动清理", "info")
                    except:
                        pass
                
                # 显示结果预览
                preview_text = f"【识别结果预览】\n{result['text'][:500]}"
                if len(result['text']) > 500:
                    preview_text += "\n\n... (未完整显示)"
                
                self.root.after(0, lambda: self.asr_result.config(state='normal'))
                self.root.after(0, lambda: self.asr_result.delete(1.0, tk.END))
                self.root.after(0, lambda pt=preview_text: self.asr_result.insert(1.0, pt))
                self.root.after(0, lambda: self.asr_result.config(state='disabled'))
                self.root.after(0, lambda: self._update_asr_progress(100, "✅ 完成！"))
            else:
                raise Exception("识别失败")
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self._asr_log(f"❌ 错误：{msg}", "error"))
            self.root.after(0, lambda: self._update_asr_progress(0, "❌ 失败"))
        
        finally:
            self.root.after(0, lambda: self._asr_task_finished())
    
    def _update_asr_progress(self, percent, message):
        """更新ASR进度"""
        self.asr_progress['value'] = percent
        self.asr_progress_var.set(f"{message}")
    
    def _asr_log(self, message, tag="info"):
        """ASR日志"""
        self.asr_log.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.asr_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.asr_log.insert(tk.END, message + "\n", tag)
        self.asr_log.see(tk.END)
        self.asr_log.config(state='disabled')
    
    def _asr_task_finished(self):
        """ASR任务完成"""
        self.asr_task_running = False
        self.asr_start_btn.config(state='normal')
    
    def get_timestamp(self):
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%H:%M:%S")
    
    def log(self, message, tag="info"):
        """添加日志"""
        self.log_text.config(state='normal')
        timestamp = self.get_timestamp()
        self.log_text.insert(tk.END, f"[{timestamp}] ", "info")
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("日志已清空")
    
    def clear_processed(self):
        """清空已处理记录"""
        self.processed_urls.clear()
        self.record_label = self.status_canvas.itemcget(self.record_label, 'text')
        # 更新显示
        self.status_canvas.itemconfig(self.record_label, text=f"已处理: {len(self.processed_urls)} 个链接")
        self.log("已清空已处理链接记录")
    
    def toggle_monitoring(self):
        """切换监控状态"""
        self.monitoring = not self.monitoring
        
        if self.monitoring:
            self.status_canvas.itemconfig(self.status_indicator, fill=self.COLORS['success'])
            self.status_canvas.itemconfig(self.status_text, text="监控中", fill=self.COLORS['success'])
            self.pause_btn.config(text="⏸️ 暂停")
            self.log("▶️ 监控已恢复")
        else:
            self.status_canvas.itemconfig(self.status_indicator, fill=self.COLORS['warning'])
            self.status_canvas.itemconfig(self.status_text, text="已暂停", fill=self.COLORS['warning'])
            self.pause_btn.config(text="▶️ 继续")
            self.log("⏸️ 监控已暂停")
    
    def start_monitoring(self):
        """开始监控剪贴板"""
        if not self.monitoring:
            return
            
        try:
            current = pyperclip.paste()
        except:
            try:
                current = self.root.clipboard_get()
            except:
                current = ""
        
        if current and current != self.last_clipboard:
            self.last_clipboard = current
            
            # 提取所有链接
            urls = self._extract_all_urls(current)
            new_urls = [u for u in urls if u not in self.processed_urls]
            
            if not new_urls:
                # 有链接但都已处理过
                pass
            elif len(new_urls) == 1:
                # 单个链接，直接下载
                url = new_urls[0]
                platform = self.downloader.detect_platform(url)
                platform_tag = f"platform_{platform[:4]}" if platform in ["抖音", "B站"] else "info"
                self.log(f"🔗 检测到{platform}链接：{url[:60]}...", platform_tag)
                
                self.processed_urls.append(url)
                self.status_canvas.itemconfig(self.record_label, 
                                              text=f"已处理: {len(self.processed_urls)} 个链接")
                
                thread = threading.Thread(target=self.download_task, args=(url, platform))
                thread.daemon = True
                thread.start()
            else:
                # 多个链接，提示是否批量下载
                self.log(f"📦 检测到 {len(new_urls)} 个链接，是否批量下载？", "warning")
                # 使用after让对话框延迟弹出，避免阻塞
                self.root.after(100, lambda urls=new_urls: self._prompt_batch_download(urls))
        
        self.check_timer = self.root.after(1000, self.start_monitoring)
    
    def _extract_all_urls(self, text):
        """从文本中提取所有支持的链接"""
        urls = []
        # 按行分割处理
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            url = self.downloader.extract_url(line)
            if url and url not in urls:
                urls.append(url)
        return urls
    
    def _prompt_batch_download(self, urls):
        """提示用户是否批量下载"""
        if len(urls) == 0:
            return
        
        platforms = [self.downloader.detect_platform(u) for u in urls]
        platform_summary = {}
        for p in platforms:
            platform_summary[p] = platform_summary.get(p, 0) + 1
        
        summary_text = "、".join([f"{p}{n}个" for p, n in platform_summary.items()])
        
        result = messagebox.askyesno(
            "批量下载确认",
            f"检测到 {len(urls)} 个视频链接：\n{summary_text}\n\n"
            f"是否跳转到「批量下载」标签页进行下载？\n"
            f"（提示：单个链接将继续在当前标签页下载）",
            icon='question'
        )
        
        if result:
            # 切换到批量下载标签页
            self.notebook.select(self.batch_tab)
            # 填入链接
            placeholder = "例如：\nhttps://v.douyin.com/xxx\nhttps://www.bilibili.com/video/xxx\nhttps://www.xiaohongshu.com/discovery/item/xxx\nhttps://v.kuaishou.com/xxx"
            self.batch_text.delete(1.0, tk.END)
            self.batch_text.insert(1.0, '\n'.join(urls))
            # 标记为已处理
            for url in urls:
                if url not in self.processed_urls:
                    self.processed_urls.append(url)
            self.status_canvas.itemconfig(self.record_label, 
                                          text=f"已处理: {len(self.processed_urls)} 个链接")
            self.log(f"📦 已切换到批量下载标签页，准备下载 {len(urls)} 个链接", "warning")
        else:
            # 只下载第一个链接
            url = urls[0]
            platform = self.downloader.detect_platform(url)
            platform_tag = f"platform_{platform[:4]}" if platform in ["抖音", "B站"] else "info"
            self.log(f"🔗 检测到{platform}链接：{url[:60]}...", platform_tag)
            
            self.processed_urls.append(url)
            self.status_canvas.itemconfig(self.record_label, 
                                          text=f"已处理: {len(self.processed_urls)} 个链接")
            
            thread = threading.Thread(target=self.download_task, args=(url, platform))
            thread.daemon = True
            thread.start()
    
    def download_task(self, url, platform):
        """下载任务"""
        platform_icon = {
            "抖音": "🎵",
            "哔哩哔哩": "📺",
            "小红书": "📕",
            "快手": "🎬"
        }.get(platform, "📹")
        
        try:
            self.log(f"📥 开始下载：{url[:50]}...")
            
            self.log("📹 正在下载视频...")
            video_result = self.downloader.download_video(
                url,
                progress_callback=lambda p, d, t, m: self.root.after(0, lambda msg=f"   视频进度: {p:.1f}%": self.log(msg, "info"))
            )
            
            video_title = video_result.get('title', '视频')
            video_file_path = video_result.get('file_path', '')
            
            if video_file_path and os.path.exists(video_file_path):
                # 添加视频到历史记录
                self.root.after(0, lambda p=platform, t=video_title, fp=video_file_path, u=url:
                              self.add_to_history(p, t, '视频', fp, u))
                self.log(f"✅ 视频下载完成 → {os.path.basename(video_file_path)}", "success")
            else:
                self.log("📹 视频下载完成", "success")
            
            if self.downloader.ffmpeg_available:
                self.log("🎵 正在提取音频...")
                audio_result = self.downloader.download_audio(
                    url,
                    progress_callback=lambda p, d, t, m: self.root.after(0, lambda msg=f"   音频进度: {p:.1f}%": self.log(msg, "info"))
                )
                
                audio_file_path = audio_result.get('file_path', '')
                if audio_file_path and os.path.exists(audio_file_path):
                    # 添加音频到历史记录
                    self.root.after(0, lambda p=platform, t=video_title, fp=audio_file_path, u=url:
                                  self.add_to_history(p, t, '音频', fp, u))
                    self.log(f"🎵 音频提取完成 → {os.path.basename(audio_file_path)}", "success")
                else:
                    self.log("🎵 音频提取完成", "success")
            else:
                self.log("⚠️ 跳过音频提取（ffmpeg不可用）", "warning")
            
            self.log("✨ 全部完成！", "success")
            
        except Exception as e:
            error_msg = str(e)
            if "ffmpeg" in error_msg.lower():
                self.log(f"⚠️ {error_msg}", "warning")
            else:
                self.log(f"❌ 下载失败：{error_msg[:100]}", "error")
    
    def open_video_folder(self):
        """打开视频文件夹"""
        folder_path = self.downloader.video_dir
        try:
            if os.name == 'nt':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            self.log(f"❌ 无法打开文件夹：{str(e)}", "error")
    
    def open_audio_folder(self):
        """打开音频文件夹"""
        folder_path = self.downloader.audio_dir
        try:
            if os.name == 'nt':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            self.log(f"❌ 无法打开文件夹：{str(e)}", "error")
    
    def on_close(self):
        """窗口关闭时停止监控"""
        if self.check_timer:
            self.root.after_cancel(self.check_timer)
        self.root.destroy()
    
    def run(self):
        """运行程序"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 初始化日志
        self.log("🚀 程序已启动，正在监控剪贴板...")
        self.log("📋 提示：复制视频链接后会自动下载视频+音频")
        self.log("📋 切换到「音频转文字」标签可进行语音识别")
        self.log("📋 切换到「下载历史」标签可查看下载记录")
        
        if not self.downloader.ffmpeg_available:
            self.log("⚠️ 警告：未检测到ffmpeg，音频功能将不可用", "warning")
            self.log("   请运行以下命令安装：winget install ffmpeg")
        
        self.log("-" * 50)
        
        self.root.mainloop()


def main():
    """主函数"""
    # 程序启动时立即设置HuggingFace环境变量（必须在import faster_whisper之前）
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
    
    # 自动将pip安装的nvidia-cublas DLL加入PATH（解决cublas64_12.dll找不到的问题）
    try:
        import glob
        import sys
        # 搜索site-packages下所有nvidia DLL目录
        site_candidates = []
        if getattr(sys, 'frozen', False):
            site_candidates.append(os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages'))
        else:
            for sp in sys.path:
                if sp.endswith('site-packages') and os.path.isdir(sp):
                    site_candidates.append(sp)
        
        for site_dir in site_candidates:
            # 匹配 nvidia/cublas/lib或bin、nvidia/cudnn/lib或bin 等目录
            for subpath in ['lib', 'bin']:
                for dll_dir in glob.glob(os.path.join(site_dir, 'nvidia', '*', subpath)):
                    if os.path.isdir(dll_dir) and any(f.endswith('.dll') for f in os.listdir(dll_dir)):
                        os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
    except Exception:
        pass
    
    print("=" * 50)
    print("短视频无水印下载器 v4.9")
    print("支持：抖音 | B站 | 小红书 | 快手")
    print("全新UI：现代化深色主题 + 批量下载 + 下载历史 + 字幕烧录 + 音频工具")
    print("安全声明：不收集数据 + 本地处理 + 开源模型 + 无第三方API")
    print("=" * 50)
    
    try:
        app = ClipboardMonitorGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()

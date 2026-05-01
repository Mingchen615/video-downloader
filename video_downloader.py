#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短视频无水印下载器 - 剪贴板监控版 + 音频转文字
支持平台：抖音、B站、小红书、快手
支持功能：视频下载、音频提取、ASR语音识别

作者：AI Assistant
版本：v4.0 - 新增音频转文字(ASR)功能

更新说明：
- v4.0: 新增音频转文字功能，支持faster-whisper语音识别
- v3.0: 全新剪贴板监控模式，复制即下载
- v2.4: 修复抖音音频提取问题，无需cookies
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
    
    def load_model(self, model_size='small', progress_callback=None):
        """加载ASR模型"""
        if self.model is not None and self.current_model_name == model_size:
            return True
        
        try:
            # 延迟导入，避免启动时卡顿
            from faster_whisper import WhisperModel
            
            if progress_callback:
                progress_callback(0, f"正在加载模型 {model_size}...")
            
            # 根据可用显存选择计算类型
            compute_type = "float16"  # GPU float16
            
            # 加载模型
            self.model = WhisperModel(
                model_size,
                device="cuda",
                compute_type=compute_type,
                download_root=None  # 使用默认缓存目录
            )
            
            self.current_model_name = model_size
            
            if progress_callback:
                progress_callback(100, f"模型 {model_size} 加载完成")
            
            return True
            
        except ImportError:
            raise Exception("请先安装 faster-whisper: pip install faster-whisper")
        except Exception as e:
            raise Exception(f"模型加载失败: {str(e)}")
    
    def transcribe(self, audio_path, model_size='small', progress_callback=None, language='zh'):
        """
        音频转文字
        
        Args:
            audio_path: 音频文件路径
            model_size: 模型大小 (tiny/base/small/medium)
            progress_callback: 进度回调函数
            language: 语言代码，'zh'为中文
        
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
        
        # 确保模型已加载
        if self.model is None or self.current_model_name != model_size:
            self.load_model(model_size, progress_callback)
        
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


# ==================== 抖音下载器 ====================
class DouyinDownloader:
    """
    抖音视频下载器
    尝试多种方式获取视频：
    1. 第三方API（api.douyin.wtf）
    2. 直接解析网页
    3. yt-dlp（需要cookies）
    """
    
    USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    API_BASE_URL = "https://api.douyin.wtf"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.douyin.com/',
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
    
    def get_video_info(self, url):
        """获取视频信息（尝试多种方式）"""
        # 方法1：尝试第三方API
        info = self._get_info_from_api(url)
        if info and info.get('video_url'):
            return info
        
        # 方法2：解析网页
        info = self._get_info_from_page(url)
        if info and info.get('video_url'):
            return info
        
        return None
    
    def _get_info_from_api(self, url):
        """使用第三方API获取视频信息"""
        try:
            api_url = f"{self.API_BASE_URL}/api"
            params = {"url": url}
            
            response = self.session.get(api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    return {
                        'title': data.get('video_title', '未获取到标题'),
                        'author': data.get('video_author', '未知作者'),
                        'duration': 0,
                        'video_url': data.get('nwm_video_url') or data.get('wm_video_url'),
                        'aweme_id': data.get('video_aweme_id'),
                    }
        except Exception:
            pass
        
        return None
    
    def _get_info_from_page(self, url):
        """从网页HTML中解析视频信息"""
        video_id = self.get_video_id_from_url(url)
        if not video_id:
            return None
        
        page_url = f'https://www.iesdouyin.com/share/video/{video_id}/'
        
        try:
            response = self.session.get(page_url, timeout=15)
            response.raise_for_status()
            html = response.text
            
            pattern = re.compile(r'window\._ROUTER_DATA\s*=\s*(.*?)</script>', re.DOTALL)
            match = pattern.search(html)
            
            if match:
                json_str = match.group(1).strip()
                data = json.loads(json_str)
                
                try:
                    page_data = data['loaderData']['video_(id)/page']
                    video_info_res = page_data.get('videoInfoRes', {})
                    items = video_info_res.get('item_list', [])
                    
                    if items:
                        item = items[0]
                        video_info = item.get('video', {})
                        
                        play_addr = video_info.get('play_addr', {})
                        url_list = play_addr.get('url_list', [])
                        
                        video_url = None
                        if url_list:
                            watermark_url = url_list[0]
                            video_url = watermark_url.replace('playwm', 'play')
                        
                        return {
                            'title': item.get('desc', f'douyin_video_{video_id}'),
                            'author': item.get('author', {}).get('nickname', '未知作者'),
                            'duration': video_info.get('duration', 0) // 1000,
                            'video_url': video_url,
                            'aweme_id': video_id,
                        }
                except (KeyError, IndexError, TypeError):
                    pass
            
        except Exception:
            pass
        
        return None
    
    def download_video(self, url, save_path, progress_callback=None):
        """下载抖音视频"""
        info = self.get_video_info(url)
        if not info:
            raise Exception("无法获取视频信息，请稍后重试或检查链接是否正确")
        
        video_url = info['video_url']
        title = info['title']
        
        if not video_url:
            raise Exception("无法获取视频下载地址，请稍后重试")
        
        clean_title = self._clean_filename(title)
        file_path = os.path.join(save_path, f"{clean_title}.mp4")
        
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(save_path, f"{clean_title}_{counter}.mp4")
            counter += 1
        
        self._download_file(video_url, file_path, progress_callback)
        
        return {
            'success': True,
            'title': title,
            'save_path': file_path
        }
    
    def _download_file(self, url, save_path, progress_callback=None):
        """下载文件到本地"""
        response = self.session.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        progress_callback(percent, downloaded, total_size)
    
    @staticmethod
    def _clean_filename(filename):
        """清理文件名中的非法字符"""
        illegal_chars = r'[\\/:*?"<>|]'
        filename = re.sub(illegal_chars, '_', filename)
        if len(filename) > 200:
            filename = filename[:200]
        filename = filename.strip(' .')
        if not filename:
            filename = 'douyin_video'
        return filename


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
        self.download_dir = self.video_dir
        
        for d in [self.video_dir, self.audio_dir, self.text_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
        
        self.douyin_downloader = DouyinDownloader()
        self.ffmpeg_available = self._check_ffmpeg()
        self.asr_engine = ASREngine()
    
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
        """下载视频"""
        platform = self.detect_platform(url)
        
        if platform == '抖音':
            return self._download_douyin(url, progress_callback)
        
        return self._download_ytdlp(url, progress_callback)
    
    def download_audio(self, url, progress_callback=None):
        """提取音频"""
        platform = self.detect_platform(url)
        
        if platform == '抖音':
            return self._download_audio_douyin(url, progress_callback)
        
        return self._download_audio_ytdlp(url, progress_callback)
    
    def _download_douyin(self, url, progress_callback=None):
        """下载抖音视频"""
        try:
            result = self.douyin_downloader.download_video(
                url, 
                self.video_dir, 
                progress_callback
            )
            return {
                'success': True,
                'title': result['title'],
                'save_path': self.video_dir,
                'file_path': result['save_path']
            }
        except Exception as e:
            raise Exception(f"抖音视频下载失败：{str(e)}")
    
    def _download_audio_douyin(self, url, progress_callback=None):
        """抖音音频提取：API下载视频 + ffmpeg转MP3"""
        if not self.ffmpeg_available:
            raise Exception("音频提取需要ffmpeg，请先安装ffmpeg")
        
        info = self.douyin_downloader.get_video_info(url)
        if not info:
            raise Exception("无法获取抖音视频信息")
        
        video_title = info['title']
        clean_title = self.clean_filename(video_title)
        
        mp3_output_path = os.path.join(self.audio_dir, f"{clean_title}.mp3")
        counter = 1
        while os.path.exists(mp3_output_path):
            mp3_output_path = os.path.join(self.audio_dir, f"{clean_title}_{counter}.mp3")
            counter += 1
        
        temp_dir = tempfile.gettempdir()
        temp_video_path = os.path.join(temp_dir, f"temp_audio_{os.getpid()}.mp4")
        
        try:
            def progress_wrapper(percent, downloaded, total):
                if progress_callback and total > 0:
                    progress_callback(percent * 0.8, downloaded, total)
            
            video_url = info['video_url']
            if not video_url:
                raise Exception("无法获取视频下载地址")
            
            self.douyin_downloader._download_file(video_url, temp_video_path, progress_wrapper)
            
            if progress_callback:
                progress_callback(80, 80, 100)
            
            subprocess.run([
                'ffmpeg', '-i', temp_video_path,
                '-vn', '-acodec', 'libmp3lame',
                '-ab', '192k',
                '-y',
                mp3_output_path
            ], check=True, capture_output=True)
            
            if progress_callback:
                progress_callback(100, 100, 100)
            
            return {
                'success': True,
                'title': video_title,
                'save_path': self.audio_dir,
                'file_path': mp3_output_path
            }
            
        finally:
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except:
                    pass
    
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
    
    def transcribe_file(self, file_path, model_size='small', progress_callback=None, language='zh'):
        """
        转写音频/视频文件为文字
        
        Args:
            file_path: 音频或视频文件路径
            model_size: 模型大小
            progress_callback: 进度回调
            language: 语言
        
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
                    language=language
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
                language=language
            )
        
        else:
            raise Exception(f"不支持的文件格式: {file_ext}，支持 mp3/wav/m4a/mp4 等")


# ==================== GUI 界面 ====================
class ClipboardMonitorGUI:
    """剪贴板监控下载器 GUI"""
    
    def __init__(self):
        self.downloader = VideoDownloader()
        self.monitoring = True
        self.last_clipboard = ""
        self.processed_urls = set()
        self.check_timer = None
        self.asr_task_running = False
        
        self.root = tk.Tk()
        self.root.title("短视频无水印下载器 v4.0 - 剪贴板监控版 + ASR")
        self.root.geometry("750x650")
        self.root.minsize(700, 550)
        self.root.resizable(True, True)
        
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        """设置界面布局"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === 下载 tab ===
        self.download_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.download_tab, text="📥 下载模式")
        self.setup_download_tab()
        
        # === ASR tab ===
        self.asr_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.asr_tab, text="🎤 音频转文字")
        self.setup_asr_tab()
    
    def setup_download_tab(self):
        """设置下载标签页"""
        main_frame = ttk.Frame(self.download_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="✨ 短视频无水印下载器 ✨", font=("微软雅黑", 16, "bold"))
        ttk.Label(title_frame, text="作者：铭晨 Vx：MingCv1", font=("微软雅黑", 9), foreground="gray").pack(anchor=tk.W)
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(title_frame, text="v4.0", foreground="gray", font=("微软雅黑", 10))
        version_label.pack(side=tk.RIGHT, pady=10)
        
        # 监控状态区域
        status_frame = ttk.LabelFrame(main_frame, text="📡 监控状态", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        status_inner = ttk.Frame(status_frame)
        status_inner.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_inner, text="🟢 监控中", font=("微软雅黑", 12, "bold"), foreground="#4CAF50")
        self.status_label.pack(side=tk.LEFT)
        
        self.pause_btn = ttk.Button(status_inner, text="⏸️ 暂停", command=self.toggle_monitoring, width=10)
        self.pause_btn.pack(side=tk.RIGHT, padx=5)
        
        self.record_label = ttk.Label(status_inner, text=f"已处理: {len(self.processed_urls)} 个链接", foreground="gray")
        self.record_label.pack(side=tk.RIGHT, padx=10)
        
        # ffmpeg状态
        ffmpeg_status = "✅ ffmpeg可用" if self.downloader.ffmpeg_available else "⚠️ ffmpeg不可用，音频功能受限"
        self.ffmpeg_label = ttk.Label(status_frame, text=ffmpeg_status, foreground="#FF9800" if not self.downloader.ffmpeg_available else "#4CAF50")
        self.ffmpeg_label.pack(anchor=tk.W)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📋 日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 10),
            relief=tk.FLAT, bg="#1E1E1E", fg="#00FF00"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志标签配置
        self.log_text.tag_configure("info", foreground="#00FF00")
        self.log_text.tag_configure("warning", foreground="#FF9800")
        self.log_text.tag_configure("error", foreground="#FF5252")
        self.log_text.tag_configure("success", foreground="#69F0AE")
        self.log_text.tag_configure("platform_douyin", foreground="#40C4FF")
        self.log_text.tag_configure("platform_bilibili", foreground="#FF6E40")
        self.log_text.tag_configure("platform_xiaohongshu", foreground="#FF4081")
        self.log_text.tag_configure("platform_kuaishou", foreground="#FFFF00")
        
        # 底部按钮
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(footer_frame, text="📂 视频文件夹", command=self.open_video_folder).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="🎵 音频文件夹", command=self.open_audio_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(footer_frame, text="🗑️ 清空日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="🔄 清空已处理", command=self.clear_processed).pack(side=tk.LEFT, padx=5)
        
        # 平台标签
        platforms_frame = ttk.Frame(main_frame)
        platforms_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(platforms_frame, text="🏷️ 支持平台：", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        
        platforms = ["抖音", "B站", "小红书", "快手"]
        for platform in platforms:
            chip = tk.Label(platforms_frame, text=platform, bg="#E8E8E8", fg="#333", padx=8, pady=2, font=("微软雅黑", 8))
            chip.pack(side=tk.LEFT, padx=2)
    
    def setup_asr_tab(self):
        """设置ASR标签页"""
        main_frame = ttk.Frame(self.asr_tab, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎤 音频转文字 (ASR)", font=("微软雅黑", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 说明
        info_frame = ttk.LabelFrame(main_frame, text="📖 使用说明", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = """
• 方式一：选择本地音频/视频文件进行转文字
• 方式二：输入视频链接，自动下载并转文字
• 支持格式：MP3、WAV、M4A、MP4、AVI等
• 输出结果：文字稿(.txt) + 字幕(.srt)
        """
        ttk.Label(info_frame, text=info_text.strip(), font=("微软雅黑", 9), justify=tk.LEFT).pack(anchor=tk.W)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="📁 选择文件", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_inner = ttk.Frame(file_frame)
        file_inner.pack(fill=tk.X)
        
        self.asr_file_path = tk.StringVar()
        ttk.Entry(file_inner, textvariable=self.asr_file_path, font=("微软雅黑", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(file_inner, text="浏览...", command=self.browse_asr_file).pack(side=tk.RIGHT)
        
        # 或链接输入
        link_frame = ttk.Frame(file_frame)
        link_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(link_frame, text="或输入链接：").pack(side=tk.LEFT)
        self.asr_link = tk.StringVar()
        ttk.Entry(link_frame, textvariable=self.asr_link, font=("微软雅黑", 10), width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 模型选择
        model_frame = ttk.LabelFrame(main_frame, text="🤖 模型设置", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        model_inner = ttk.Frame(model_frame)
        model_inner.pack(fill=tk.X)
        
        ttk.Label(model_inner, text="模型大小：").pack(side=tk.LEFT)
        
        self.asr_model_var = tk.StringVar(value='small')
        model_combo = ttk.Combobox(
            model_inner,
            textvariable=self.asr_model_var,
            values=['tiny', 'base', 'small', 'medium'],
            state='readonly',
            width=10
        )
        model_combo.pack(side=tk.LEFT, padx=5)
        
        # 模型推荐说明
        model_desc = ttk.Label(model_inner, text="推荐 small/medium（中文效果好）", foreground="gray")
        model_desc.pack(side=tk.LEFT, padx=10)
        
        # 语言选择
        lang_inner = ttk.Frame(model_frame)
        lang_inner.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(lang_inner, text="识别语言：").pack(side=tk.LEFT)
        
        self.asr_lang_var = tk.StringVar(value='zh')
        lang_combo = ttk.Combobox(
            lang_inner,
            textvariable=self.asr_lang_var,
            values=[('zh', '中文'), ('en', '英文'), ('auto', '自动检测')],
            state='readonly',
            width=15
        )
        lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 开始按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.asr_start_btn = ttk.Button(
            btn_frame,
            text="🎤 开始转写",
            command=self.start_asr_task,
            style="Accent.TButton"
        )
        self.asr_start_btn.pack(side=tk.LEFT)
        
        self.asr_progress_var = tk.StringVar(value="")
        ttk.Label(btn_frame, textvariable=self.asr_progress_var, foreground="#4CAF50").pack(side=tk.LEFT, padx=20)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📋 识别日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.asr_log = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 10),
            relief=tk.FLAT, bg="#1E1E1E", fg="#00FF00",
            height=12
        )
        self.asr_log.pack(fill=tk.BOTH, expand=True)
        self.asr_log.tag_configure("info", foreground="#00FF00")
        self.asr_log.tag_configure("warning", foreground="#FF9800")
        self.asr_log.tag_configure("error", foreground="#FF5252")
        self.asr_log.tag_configure("success", foreground="#69F0AE")
        
        # 结果预览
        result_frame = ttk.LabelFrame(main_frame, text="📝 转写结果预览", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.asr_result = scrolledtext.ScrolledText(
            result_frame, wrap=tk.WORD, font=("微软雅黑", 10),
            relief=tk.FLAT, bg="#F5F5F5",
            height=6
        )
        self.asr_result.pack(fill=tk.BOTH, expand=True)
    
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
        
        if not file_path and not link:
            messagebox.showwarning("提示", "请选择文件或输入视频链接")
            return
        
        self.asr_task_running = True
        self.asr_start_btn.config(state='disabled')
        self.asr_progress_var.set("准备中...")
        self.asr_result.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._asr_task, args=(file_path, link))
        thread.daemon = True
        thread.start()
    
    def _asr_task(self, file_path, link):
        """ASR转写任务（在线程中运行）"""
        try:
            model_size = self.asr_model_var.get()
            language = self.asr_lang_var.get()
            
            def progress_callback(percent, message):
                self.root.after(0, lambda: self._update_asr_progress(percent, message))
            
            def log_callback(message, tag="info"):
                self.root.after(0, lambda: self._asr_log(message, tag))
            
            progress_callback(0, "正在处理...")
            log_callback("开始语音识别...", "info")
            
            if link:
                # 从链接下载并转写
                log_callback(f"📥 正在下载视频：{link[:50]}...", "info")
                
                # 下载视频
                video_result = self.downloader.download_video(
                    link,
                    progress_callback=lambda p, d, t: self.root.after(0, lambda: self._asr_log(f"   下载进度: {p:.1f}%", "info"))
                )
                
                if video_result.get('file_path') and os.path.exists(video_result['file_path']):
                    file_path = video_result['file_path']
                    log_callback(f"✅ 视频下载完成：{os.path.basename(file_path)}", "success")
                else:
                    raise Exception("视频下载失败")
            
            if not file_path or not os.path.exists(file_path):
                raise Exception(f"文件不存在：{file_path}")
            
            log_callback(f"🎤 开始识别：{os.path.basename(file_path)}", "info")
            
            # 执行转写
            result = self.downloader.transcribe_file(
                file_path,
                model_size=model_size,
                progress_callback=progress_callback,
                language=language
            )
            
            if result['success']:
                log_callback("=" * 50, "success")
                log_callback(f"✅ 识别完成！", "success")
                log_callback(f"📄 语言：{result['language']} (概率: {result['language_prob']:.1%})", "success")
                log_callback(f"⏱️ 时长：{result['duration']:.1f} 秒", "success")
                log_callback(f"📝 文字稿：{os.path.basename(result['txt_path'])}", "success")
                log_callback(f"📝 字幕：{os.path.basename(result['srt_path'])}", "success")
                log_callback("=" * 50, "success")
                
                # 显示结果预览
                preview_text = f"【识别结果预览】\n{result['text'][:500]}"
                if len(result['text']) > 500:
                    preview_text += "\n\n... (未完整显示)"
                
                self.root.after(0, lambda: self.asr_result.delete(1.0, tk.END))
                self.root.after(0, lambda: self.asr_result.insert(1.0, preview_text))
                self.root.after(0, lambda: self._update_asr_progress(100, "✅ 完成！"))
            else:
                raise Exception("识别失败")
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._asr_log(f"❌ 错误：{error_msg}", "error"))
            self.root.after(0, lambda: self._update_asr_progress(0, "❌ 失败"))
        
        finally:
            self.root.after(0, lambda: self._asr_task_finished())
    
    def _update_asr_progress(self, percent, message):
        """更新ASR进度"""
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
        self.record_label.config(text=f"已处理: {len(self.processed_urls)} 个链接")
        self.log("已清空已处理链接记录")
    
    def toggle_monitoring(self):
        """切换监控状态"""
        self.monitoring = not self.monitoring
        
        if self.monitoring:
            self.status_label.config(text="🟢 监控中", foreground="#4CAF50")
            self.pause_btn.config(text="⏸️ 暂停")
            self.log("▶️ 监控已恢复")
        else:
            self.status_label.config(text="⏸️ 已暂停", foreground="#FF9800")
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
            
            url = self.downloader.extract_url(current)
            
            if url and url not in self.processed_urls:
                platform = self.downloader.detect_platform(url)
                platform_tag = f"platform_{platform[:4]}" if platform in ["抖音", "B站"] else "info"
                self.log(f"🔗 检测到{platform}链接：{url[:60]}...", platform_tag)
                
                self.processed_urls.add(url)
                self.record_label.config(text=f"已处理: {len(self.processed_urls)} 个链接")
                
                thread = threading.Thread(target=self.download_task, args=(url, platform))
                thread.daemon = True
                thread.start()
        
        self.check_timer = self.root.after(1000, self.start_monitoring)
    
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
                progress_callback=lambda p, d, t: self.root.after(0, lambda: self.log(f"   视频进度: {p:.1f}%", "info"))
            )
            
            if video_result.get('file_path') and os.path.exists(video_result['file_path']):
                self.log(f"✅ 视频下载完成 → {os.path.basename(video_result['file_path'])}", "success")
            else:
                self.log("📹 视频下载完成", "success")
            
            if self.downloader.ffmpeg_available:
                self.log("🎵 正在提取音频...")
                audio_result = self.downloader.download_audio(
                    url,
                    progress_callback=lambda p, d, t: self.root.after(0, lambda: self.log(f"   音频进度: {p:.1f}%", "info"))
                )
                
                if audio_result.get('file_path') and os.path.exists(audio_result['file_path']):
                    self.log(f"🎵 音频提取完成 → {os.path.basename(audio_result['file_path'])}", "success")
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
        
        if not self.downloader.ffmpeg_available:
            self.log("⚠️ 警告：未检测到ffmpeg，音频功能将不可用", "warning")
            self.log("   请运行以下命令安装：winget install ffmpeg")
        
        self.log("-" * 50)
        
        self.root.mainloop()


def main():
    """主函数"""
    print("=" * 50)
    print("短视频无水印下载器 v4.0")
    print("支持：抖音 | B站 | 小红书 | 快手")
    print("新增功能：音频转文字 (ASR)")
    print("=" * 50)
    
    try:
        app = ClipboardMonitorGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()

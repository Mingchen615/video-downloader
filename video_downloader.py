#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短视频无水印下载器 - 剪贴板监控版
支持平台：抖音、B站、小红书、快手

作者：AI Assistant
版本：v3.0 - 剪贴板监控模式，复制即下载

更新说明：
- v3.0: 全新剪贴板监控模式，复制视频链接自动下载视频+音频
- v2.4: 修复抖音音频提取问题，无需cookies
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
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


class VideoDownloader:
    """短视频下载器核心类"""
    
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = os.path.join(self.script_dir, "downloads", "视频")
        self.audio_dir = os.path.join(self.script_dir, "downloads", "音频")
        self.download_dir = self.video_dir
        
        for d in [self.video_dir, self.audio_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
        
        self.douyin_downloader = DouyinDownloader()
        self.ffmpeg_available = self._check_ffmpeg()
    
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


class ClipboardMonitorGUI:
    """剪贴板监控下载器 GUI"""
    
    def __init__(self):
        self.downloader = VideoDownloader()
        self.monitoring = True
        self.last_clipboard = ""
        self.processed_urls = set()  # 已处理链接集合
        self.check_timer = None
        
        self.root = tk.Tk()
        self.root.title("短视频无水印下载器 v3.0 - 剪贴板监控版")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)
        
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        """设置界面布局"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === 标题区域 ===
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="✨ 短视频无水印下载器 ✨", font=("微软雅黑", 16, "bold"))
        ttk.Label(title_frame, text="作者：铭晨 Vx：MingCv1", font=("微软雅黑", 9), foreground="gray").pack(anchor=tk.W)
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(title_frame, text="v3.0", foreground="gray", font=("微软雅黑", 10))
        version_label.pack(side=tk.RIGHT, pady=10)
        
        # === 监控状态区域 ===
        status_frame = ttk.LabelFrame(main_frame, text="📡 监控状态", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        status_inner = ttk.Frame(status_frame)
        status_inner.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_inner, text="🟢 监控中", font=("微软雅黑", 12, "bold"), foreground="#4CAF50")
        self.status_label.pack(side=tk.LEFT)
        
        self.pause_btn = ttk.Button(status_inner, text="⏸️ 暂停", command=self.toggle_monitoring, width=10)
        self.pause_btn.pack(side=tk.RIGHT, padx=5)
        
        # 处理记录数
        self.record_label = ttk.Label(status_inner, text=f"已处理: {len(self.processed_urls)} 个链接", foreground="gray")
        self.record_label.pack(side=tk.RIGHT, padx=10)
        
        # ffmpeg状态
        ffmpeg_status = "✅ ffmpeg可用" if self.downloader.ffmpeg_available else "⚠️ ffmpeg不可用，音频功能受限"
        self.ffmpeg_label = ttk.Label(status_frame, text=ffmpeg_status, foreground="#FF9800" if not self.downloader.ffmpeg_available else "#4CAF50")
        self.ffmpeg_label.pack(anchor=tk.W)
        
        # === 日志区域 ===
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
        
        # === 底部按钮区域 ===
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
    
    def get_timestamp(self):
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%H:%M:%S")
    
    def log(self, message, tag="info"):
        """添加日志"""
        timestamp = self.get_timestamp()
        self.log_text.config(state='normal')
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
            # 使用pyperclip获取剪贴板内容
            current = pyperclip.paste()
        except:
            try:
                current = self.root.clipboard_get()
            except:
                current = ""
        
        # 检查是否有变化且是新链接
        if current and current != self.last_clipboard:
            self.last_clipboard = current
            
            # 提取URL
            url = self.downloader.extract_url(current)
            
            if url and url not in self.processed_urls:
                # 检测平台
                platform = self.downloader.detect_platform(url)
                platform_tag = f"platform_{platform[:4]}" if platform in ["抖音", "B站"] else "info"
                self.log(f"🔗 检测到{platform}链接：{url[:60]}...", platform_tag)
                
                # 标记为已处理
                self.processed_urls.add(url)
                self.record_label.config(text=f"已处理: {len(self.processed_urls)} 个链接")
                
                # 启动下载
                thread = threading.Thread(target=self.download_task, args=(url, platform))
                thread.daemon = True
                thread.start()
        
        # 1秒后继续监控
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
            
            # 下载视频
            self.log("📹 正在下载视频...")
            video_result = self.downloader.download_video(
                url,
                progress_callback=lambda p, d, t: self.root.after(0, lambda: self.log(f"   视频进度: {p:.1f}%", "info"))
            )
            
            if video_result.get('file_path') and os.path.exists(video_result['file_path']):
                self.log(f"✅ 视频下载完成 → {os.path.basename(video_result['file_path'])}", "success")
            else:
                self.log("📹 视频下载完成", "success")
            
            # 下载音频（如果ffmpeg可用）
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
        # 居中窗口
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 初始化日志
        self.log("🚀 程序已启动，正在监控剪贴板...")
        self.log("📋 提示：复制视频链接后会自动下载视频+音频")
        
        if not self.downloader.ffmpeg_available:
            self.log("⚠️ 警告：未检测到ffmpeg，音频功能将不可用", "warning")
            self.log("   请运行以下命令安装：winget install ffmpeg")
        
        self.log("-" * 50)
        
        self.root.mainloop()


def main():
    """主函数"""
    print("=" * 50)
    print("短视频无水印下载器 v3.0 - 剪贴板监控版")
    print("支持：抖音 | B站 | 小红书 | 快手")
    print("=" * 50)
    
    try:
        app = ClipboardMonitorGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()

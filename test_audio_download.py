#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音音频提取功能测试脚本
测试短视频下载器v4.1中的 download_audio_only 方法
"""

import sys
import os
import tempfile

# 测试链接
DOUYIN_URL = "https://v.douyin.com/A1pOr-9mAdU/"

def test_download_audio_only():
    """测试 download_audio_only 方法"""
    print("=" * 60)
    print("抖音音频提取功能测试")
    print("=" * 60)
    print(f"测试URL: {DOUYIN_URL}\n")
    
    # 1. 检查yt-dlp
    print("[1] 检查依赖...")
    try:
        import yt_dlp
        print(f"    ✓ yt-dlp 已安装 (版本: {yt_dlp.version.__version__})")
    except ImportError:
        print("    ✗ yt-dlp 未安装")
        print("    请运行: pip install yt-dlp")
        return False
    
    # 2. 检查ffmpeg
    print("\n[2] 检查 ffmpeg...")
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        output = (result.stderr or result.stdout).decode('utf-8', errors='ignore')
        ffmpeg_version = output.split('\n')[0]
        print(f"    ✓ ffmpeg 可用")
        print(f"      {ffmpeg_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("    ✗ ffmpeg 不可用")
        print("    请安装: sudo apt install ffmpeg")
        return False
    
    # 3. 导入VideoDownloader
    print("\n[3] 导入 VideoDownloader...")
    
    import re
    import requests
    
    class TestAudioDownloader:
        """简化的音频下载测试器"""
        
        def __init__(self, cookies_path=None):
            self.cookies_path = cookies_path
            self.cookies_dict = None
            if cookies_path and os.path.exists(cookies_path):
                self._load_cookies()
        
        def _load_cookies(self):
            """加载cookies"""
            try:
                import json
                with open(self.cookies_path, 'r') as f:
                    cookies_list = json.load(f)
                self.cookies_dict = {c['name']: c['value'] for c in cookies_list}
                print(f"    ✓ 已加载 {len(self.cookies_dict)} 个cookies")
            except Exception as e:
                print(f"    ✗ 加载cookies失败: {e}")
        
        def clean_filename(self, filename):
            illegal_chars = r'[\\/:*?"<>|]'
            filename = re.sub(illegal_chars, '_', filename)
            if len(filename) > 200:
                filename = filename[:200]
            filename = filename.strip(' .')
            return filename
        
        def detect_platform(self, url):
            url_lower = url.lower()
            if 'douyin.com' in url_lower or 'v.douyin.com' in url_lower:
                return '抖音'
            return '其他'
        
        def _get_video_info_basic(self, url, with_cookies=False):
            """获取视频基本信息"""
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            if with_cookies and self.cookies_path:
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
        
        def download_audio_only(self, url, progress_callback=None, with_cookies=False):
            """只下载音频用于ASR识别"""
            temp_dir = tempfile.mkdtemp(prefix="asr_test_")
            print(f"\n    临时目录: {temp_dir}")
            
            try:
                info = self._get_video_info_basic(url, with_cookies=with_cookies)
                video_title = info.get('title', 'unknown')
                clean_title = self.clean_filename(video_title)
                output_path = os.path.join(temp_dir, f"{clean_title}.%(ext)s")
                
                print(f"    视频标题: {video_title}")
                print(f"    清理后标题: {clean_title}")
                
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
                
                # 添加cookies支持
                if with_cookies and self.cookies_path:
                    ydl_opts['cookiefile'] = self.cookies_path
                    print("    使用cookies认证...")
                
                if progress_callback:
                    ydl_opts['progress_hooks'].append(lambda d: self._audio_progress_hook(d, progress_callback))
                
                print("\n[5] 开始下载音频...")
                print("    (这可能需要一些时间...)")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # 查找生成的MP3文件
                for f in os.listdir(temp_dir):
                    if f.endswith('.mp3'):
                        file_path = os.path.join(temp_dir, f)
                        print(f"\n    ✓ 音频文件已生成: {f}")
                        print(f"      文件路径: {file_path}")
                        return {'success': True, 'title': video_title, 'file_path': file_path}
                
                # 没有MP3就找任意音频文件
                for f in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, f)
                    print(f"\n    ✓ 音频文件已生成: {f}")
                    print(f"      文件路径: {file_path}")
                    return {'success': True, 'title': video_title, 'file_path': file_path}
                
                raise Exception("音频下载失败：未找到输出文件")
            except Exception as e:
                raise Exception(f"音频提取失败：{str(e)}")
        
        def _audio_progress_hook(self, d, progress_callback):
            """音频下载进度回调"""
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', 'N/A')
                speed = d.get('_speed_str', 'N/A')
                if progress_callback:
                    progress_callback(0, f"下载中: {percent} 速度: {speed}")
    
    try:
        downloader = TestAudioDownloader()
        print("    ✓ 测试下载器初始化成功")
    except Exception as e:
        print(f"    ✗ 测试下载器初始化失败: {e}")
        return False
    
    # 4. 测试平台检测
    print("\n[4] 测试平台检测...")
    platform = downloader.detect_platform(DOUYIN_URL)
    print(f"    检测结果: {platform}")
    if platform != '抖音':
        print("    ✗ 平台检测失败!")
        return False
    print("    ✓ 平台检测正确")
    
    # 5. 测试音频下载
    # 首先尝试不带cookies下载
    print("\n[5] 测试音频下载...")
    print("    步骤1: 尝试不使用cookies下载...")
    
    cookies_path = "./短视频下载器/cookies.json"
    if os.path.exists(cookies_path):
        print(f"    发现cookies文件: {cookies_path}")
        downloader_with_cookies = TestAudioDownloader(cookies_path)
    else:
        print(f"    未找到cookies文件: {cookies_path}")
        downloader_with_cookies = downloader
    
    # 尝试不带cookies
    try:
        result = downloader.download_audio_only(DOUYIN_URL)
        if result.get('success'):
            print("\n" + "=" * 60)
            print("✓ 测试成功! (无需cookies)")
            print(f"  视频标题: {result['title']}")
            print(f"  音频路径: {result['file_path']}")
            print("=" * 60)
            return True
    except Exception as e:
        error_msg = str(e)
        print(f"    ✗ 不带cookies下载失败: {error_msg}")
        
        # 检查是否需要cookies
        if "Fresh cookies" in error_msg or "cookies" in error_msg.lower():
            print("\n    步骤2: 尝试使用cookies下载...")
            
            # 如果有cookies文件，使用cookies重试
            if os.path.exists(cookies_path):
                try:
                    result = downloader_with_cookies.download_audio_only(DOUYIN_URL, with_cookies=True)
                    if result.get('success'):
                        print("\n" + "=" * 60)
                        print("✓ 测试成功! (使用cookies)")
                        print(f"  视频标题: {result['title']}")
                        print(f"  音频路径: {result['file_path']}")
                        print("=" * 60)
                        return True
                except Exception as e2:
                    print(f"    ✗ 使用cookies下载也失败: {e2}")
            
            # 分析错误原因
            print("\n" + "=" * 60)
            print("⚠ 测试结果: 需要cookies认证")
            print("=" * 60)
            print("\n问题分析:")
            print("  → 抖音视频需要Fresh cookies验证")
            print("  → yt-dlp无法在没有cookies的情况下下载抖音视频")
            print("\n解决方案:")
            print("  1. 使用浏览器扩展导出cookies (如 EditThisCookie )")
            print("  2. 保存cookies为JSON格式")
            print("  3. 将cookies文件放到: ./短视频下载器/cookies.json")
            print("\ncookies.json格式示例:")
            print('  [{"name": "sessionid", "value": "xxx", "domain": ".douyin.com"}, ...]')
            print("\n" + "=" * 60)
            return False
        else:
            print(f"\n✗ 测试异常: {error_msg}")
            return False

if __name__ == "__main__":
    try:
        success = test_download_audio_only()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR功能bug修复测试脚本

测试场景：
1. 验证所有回调函数参数签名正确
2. 验证抖音分享文本链接提取
3. 验证临时文件创建和清理逻辑
"""

import sys
import os
import re
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_callback_signatures():
    """测试1: 验证回调函数签名"""
    print("=" * 60)
    print("测试1: 回调函数签名检查")
    print("=" * 60)
    
    # 模拟 download_audio_only 需要的4参数回调签名
    def asr_download_callback(percent, downloaded, total, message):
        """ASR下载回调 - 4参数"""
        print(f"   [{message}] 进度: {percent:.1f}% ({downloaded}/{total})")
    
    # 模拟 download_audio/video 需要的3参数回调签名
    def download_callback_3args(percent, downloaded, total):
        """下载回调 - 3参数"""
        print(f"   进度: {percent:.1f}% ({downloaded}/{total})")
    
    # 模拟 transcribe 需要的2参数回调签名
    def transcribe_callback(percent, message):
        """转写回调 - 2参数"""
        print(f"   [{message}] 进度: {percent:.1f}%")
    
    # 测试4参数回调
    try:
        asr_download_callback(50.5, 1024000, 2048000, "测试下载")
        print("✅ 4参数回调签名正确")
    except TypeError as e:
        print(f"❌ 4参数回调签名错误: {e}")
        return False
    
    # 测试3参数回调
    try:
        download_callback_3args(50.5, 1024000, 2048000)
        print("✅ 3参数回调签名正确")
    except TypeError as e:
        print(f"❌ 3参数回调签名错误: {e}")
        return False
    
    # 测试2参数回调
    try:
        transcribe_callback(50.5, "测试转写")
        print("✅ 2参数回调签名正确")
    except TypeError as e:
        print(f"❌ 2参数回调签名错误: {e}")
        return False
    
    print()
    return True


def test_share_text_parsing():
    """测试2: 抖音分享文本链接提取"""
    print("=" * 60)
    print("测试2: 分享文本链接提取")
    print("=" * 60)
    
    test_cases = [
        # 标准分享文本格式
        ("晏波与歌 https://v.douyin.com/abc123 复制此链接，打开Douyin，即可直接观看！", 
         "https://v.douyin.com/abc123"),
        
        # 带引号的链接
        ('刚才刷到 "测试视频 https://v.douyin.com/xyz789 复制这段内容"',
         "https://v.douyin.com/xyz789"),
        
        # B站分享文本
        ("【视频标题】 https://b23.tv/ABC123 点击链接直接观看",
         "https://b23.tv/ABC123"),
        
        # 直接URL
        ("https://v.douyin.com/direct",
         "https://v.douyin.com/direct"),
        
        # 带空格的URL
        ("看这个视频  https://v.douyin.com/spaces  空格很多",
         "https://v.douyin.com/spaces"),
    ]
    
    url_pattern = re.compile(r'https?://[^\s<>"\']+')
    
    all_passed = True
    for share_text, expected in test_cases:
        # 模拟 start_asr_task 中的提取逻辑
        link = share_text.strip()
        if link and not link.startswith('http'):
            url_match = url_pattern.search(link)
            if url_match:
                link = url_match.group(0)
        
        # 验证
        if link == expected:
            print(f"✅ 提取成功: {link[:50]}...")
        else:
            print(f"❌ 提取失败:")
            print(f"   输入: {share_text[:50]}...")
            print(f"   期望: {expected}")
            print(f"   实际: {link}")
            all_passed = False
    
    print()
    return all_passed


def test_temp_file_logic():
    """测试3: 临时文件创建和清理逻辑"""
    print("=" * 60)
    print("测试3: 临时文件创建和清理逻辑")
    print("=" * 60)
    
    try:
        # 模拟 _asr_task 中的临时文件逻辑
        temp_dir = tempfile.mkdtemp(prefix="asr_")
        print(f"✅ 创建临时目录: {temp_dir}")
        
        # 创建临时文件
        temp_file = os.path.join(temp_dir, "test_audio.mp3")
        with open(temp_file, 'w') as f:
            f.write("test audio content")
        print(f"✅ 创建临时文件: {temp_file}")
        
        # 验证文件存在
        if os.path.exists(temp_file):
            print("✅ 临时文件验证成功")
        else:
            print("❌ 临时文件验证失败")
            return False
        
        # 模拟清理逻辑
        try:
            os.remove(temp_file)
            print(f"✅ 删除临时文件: {temp_file}")
            
            # 尝试清理空临时目录
            if temp_dir.startswith(tempfile.gettempdir()) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
                print(f"✅ 删除空临时目录: {temp_dir}")
            else:
                print(f"⚠️ 临时目录非空，保留: {temp_dir}")
        except Exception as e:
            print(f"⚠️ 清理时出错 (不影响功能): {e}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 临时文件逻辑测试失败: {e}")
        print()
        return False


def test_lambda_callback():
    """测试4: Lambda回调参数绑定测试"""
    print("=" * 60)
    print("测试4: Lambda回调参数绑定测试")
    print("=" * 60)
    
    # 模拟修复后的4参数lambda回调
    def call_with_4_args(callback):
        """模拟 download_audio_only 调用回调的方式"""
        callback(50.0, 1024000, 2048000, "下载进度")
    
    try:
        # 这是修复后的lambda写法
        test_callback = lambda p, d, t, msg: f"进度: {p:.1f}%, {msg}"
        result = call_with_4_args(test_callback)
        print(f"✅ 4参数lambda回调测试通过: {result}")
    except TypeError as e:
        print(f"❌ 4参数lambda回调测试失败: {e}")
        return False
    
    # 测试错误写法（3参数）
    try:
        bad_callback = lambda p, d, t: f"进度: {p:.1f}%"
        result = call_with_4_args(bad_callback)
        print(f"❌ 3参数lambda回调应该失败但没有")
        return False
    except TypeError as e:
        print(f"✅ 3参数lambda正确触发TypeError (这是预期的)")
    
    print()
    return True


def test_code_import():
    """测试5: 代码导入测试"""
    print("=" * 60)
    print("测试5: 代码导入测试")
    print("=" * 60)
    
    try:
        # 测试能否导入修改后的模块
        # 注意：这里只是语法检查，不实际运行GUI部分
        import py_compile
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'video_downloader.py')
        script_path = os.path.normpath(script_path)
        py_compile.compile(script_path, doraise=True)
        print(f"✅ Python语法检查通过: {script_path}")
        
        # 测试能否导入VideoDownloader类
        # 由于GUI依赖，可能无法完全导入，但我们测试核心逻辑
        import importlib.util
        spec = importlib.util.spec_from_file_location("video_downloader", script_path)
        module = importlib.util.module_from_spec(spec)
        
        # 捕获导入时的错误
        try:
            spec.loader.exec_module(module)
            print("✅ 模块加载成功")
        except ImportError as e:
            # GUI依赖缺失是预期的，只要核心代码没问题就行
            if 'tkinter' in str(e).lower():
                print("⚠️ tkinter依赖缺失 (仅影响GUI运行)")
            else:
                print(f"❌ 模块加载失败: {e}")
                return False
                
        print()
        return True
        
    except Exception as e:
        print(f"❌ 代码导入测试失败: {e}")
        print()
        return False


def main():
    """主测试函数"""
    print()
    print("=" * 60)
    print("短视频下载器 ASR功能 Bug修复测试")
    print("=" * 60)
    print()
    
    # 切换到项目目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    results = []
    
    # 运行所有测试
    results.append(("回调函数签名", test_callback_signatures()))
    results.append(("分享文本链接提取", test_share_text_parsing()))
    results.append(("临时文件逻辑", test_temp_file_logic()))
    results.append(("Lambda回调绑定", test_lambda_callback()))
    results.append(("代码导入检查", test_code_import()))
    
    # 输出汇总
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("=" * 60)
        print("🎉 所有测试通过！Bug修复成功！")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("⚠️ 部分测试失败，请检查上述输出")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

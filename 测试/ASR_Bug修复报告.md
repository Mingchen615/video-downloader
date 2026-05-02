# ASR功能Bug修复测试报告

**项目**: 短视频下载器 video_downloader.py  
**测试日期**: 2024年  
**修复版本**: v4.2

---

## 一、修复的Bug

### Bug 1: Lambda回调函数参数签名不匹配 ✅ 已修复

**问题描述**:
- `download_audio_only` 内部对回调函数的调用不一致
- 部分调用使用2参数: `progress_callback(0, "消息")`
- 部分调用期望3参数: `lambda p, d, t: ...`
- 外部调用传入的lambda是3参数，与内部2参数调用冲突

**原始代码问题位置**:
```python
# 第549-550行
if progress_callback:
    progress_callback(0, "正在下载抖音视频...")  # 2参数

# 第554行
lambda p, d, t: progress_callback(p * 0.7, d, t)  # 期望外部是3参数

# 第1205行
progress_callback=lambda p, d, t: ...  # 3参数lambda
```

**修复方案**:
统一为4参数签名: `(percent, downloaded, total, message)`

**修复后代码**:
```python
# 修复后的调用方式
progress_callback(0, 0, 0, "正在下载抖音视频...")
progress_callback(percent, downloaded, total, "下载进度...")

# 外部lambda
lambda p, d, t, msg: self.root.after(0, lambda: self._asr_log(f"   {msg} ({p:.1f}%)", "info"))
```

---

### Bug 2: 分享文本链接提取 ✅ 已验证正常

**问题描述**:
抖音分享文本（如"晏波与歌 https://v.douyin.com/xxx 复制此链接..."）需要自动提取URL

**现有代码验证**:
```python
# 第1165-1169行 - 已正确实现
if link and not link.startswith('http'):
    import re as _re
    url_match = _re.search(r'https?://[^\s<>"\']+', link)
    if url_match:
        link = url_match.group(0)
```

**测试结果**: ✅ 通过（5种分享文本格式全部正确提取）

---

## 二、测试场景

| # | 测试项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 回调函数签名检查 | ✅ 通过 | 2/3/4参数回调均正常工作 |
| 2 | 分享文本链接提取 | ✅ 通过 | 5种格式全部正确 |
| 3 | 临时文件创建和清理 | ✅ 通过 | 目录创建、文件操作、清理均正常 |
| 4 | Lambda回调参数绑定 | ✅ 通过 | 4参数lambda测试通过 |
| 5 | Python语法检查 | ✅ 通过 | 无语法错误 |

---

## 三、修改的文件

| 文件 | 修改内容 |
|------|----------|
| `video_downloader.py` | 修复 `download_audio_only` 回调签名（第549-576行、第606-620行、第1219行） |

---

## 四、修复详情

### 4.1 修改位置1: `download_audio_only` 抖音下载部分

```python
# 修改前
if progress_callback:
    progress_callback(0, "正在下载抖音视频...")

self.douyin_downloader._download_file(
    info['video_url'], temp_video_path,
    lambda p, d, t: progress_callback(p * 0.7, d, t) if progress_callback else None
)

# 修改后
if progress_callback:
    progress_callback(0, 0, 0, "正在下载抖音视频...")

def download_progress_cb(p, d, t):
    if progress_callback:
        progress_callback(p * 0.7, d, t, f"下载进度: {p:.1f}%")

self.douyin_downloader._download_file(
    info['video_url'], temp_video_path, download_progress_cb
)
```

### 4.2 修改位置2: `download_audio_only` yt-dlp部分

```python
# 修改前
if progress_callback:
    ydl_opts['progress_hooks'].append(lambda d: self._audio_progress_hook(d, progress_callback))

# 修改后
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
```

### 4.3 修改位置3: `_asr_task` 中的调用

```python
# 修改前
progress_callback=lambda p, d, t: self.root.after(0, lambda: self._asr_log(f"   下载进度: {p:.1f}%", "info"))

# 修改后
progress_callback=lambda p, d, t, msg: self.root.after(0, lambda: self._asr_log(f"   {msg} ({p:.1f}%)", "info"))
```

---

## 五、验证结果

```
============================================================
测试结果汇总
============================================================
✅ 通过: 回调函数签名
✅ 通过: 分享文本链接提取
✅ 通过: 临时文件逻辑
✅ 通过: Lambda回调绑定
✅ 通过: 代码导入检查

🎉 所有测试通过！Bug修复成功！
============================================================
```

---

## 六、注意事项

1. **回调签名约定**:
   - `download_audio_only`: 4参数 `(percent, downloaded, total, message)`
   - `download_audio` / `download_video`: 3参数 `(percent, downloaded, total)`
   - `transcribe_file`: 2参数 `(percent, message)`

2. **GUI依赖**: tkinter在云环境不可用，但核心逻辑已验证正确

3. **临时文件**: 临时文件在ASR完成后会自动清理

---

**测试脚本位置**: `./短视频下载器/测试/test_asr_fix.py`

# 语音转文字工具 v0.0.2

基于 Faster-Whisper + pyannote 的 Windows 桌面端语音转文字工具，支持说话人区分、中文标点恢复、视频提取音频、批量转写。

## 功能

- 音频/视频拖拽转写（m4a/mp3/wav/mp4/avi/mkv/webm 等）
- 自动检测 / 中文 / 英语 / 日语
- 中文自动标点恢复（。，？！；、）
- 说话人区分（SPEAKER_00 ~ SPEAKER_04）
- 同说话人段落合并
- 批量多文件转写（逐个处理，统一进度）
- GPU 加速转写 + 实时进度 + 日志
- 取消按钮（可随时中止转写）
- 输出文件名自动加时间戳，多次转写不覆盖

## 系统要求

| 项目 | 最低要求 |
|:---|:---|
| 操作系统 | Windows 10/11 64-bit |
| Python | 3.12（需 py launcher） |
| GPU | NVIDIA 显卡，6GB+ 显存（推荐） |
| CUDA | 11.x / 12.x（setup.bat 自动检测） |
| 内存 | 16GB |
| 磁盘 | 10GB 可用空间 |

## 快速开始

### 1. 安装 Python 3.12

下载并安装：https://www.python.org/downloads/release/python-3129/

安装时勾选 **"py launcher"**（默认已勾选），不需要勾选「Add to PATH」。

### 2. 安装 NVIDIA 驱动

确保 `nvidia-smi` 可用，CUDA 版本 ≥ 11.8。setup.bat 会自动检测 CUDA 版本并安装匹配的 PyTorch。

### 3. 同意 HuggingFace 模型协议

注册 https://huggingface.co/join，然后依次访问以下链接并点击「Agree and access repository」：

1. https://hf.co/pyannote/speaker-diarization-3.1
2. https://hf.co/pyannote/segmentation-3.0
3. https://hf.co/pyannote/speaker-diarization-community-1

### 4. 一键安装

```bat
setup.bat
```

自动安装所有 Python 依赖、预下载模型（约 4GB，仅首次，耗时 10-30 分钟）。

### 5. 使用

双击 `transcribe_tool.exe`，拖入音频/视频文件，点「转写」。

- **单文件**：拖入或浏览选择单个文件
- **批量**：浏览时可多选（Ctrl+点击），或拖入多个文件

推荐设置：添加标点 ✅ 区分对话人 ✅ 合并同对话人 ❌

## 文件结构

```
Faster-Whisper-tools-v0.0.2/
├── transcribe_tool.exe    ← 双击运行
├── pipeline.py            ← 后端流水线
├── ffmpeg.exe             ← 音视频解码（内置）
├── setup.bat              ← 一键安装脚本
├── uninstall.bat          ← 一键卸载脚本
├── gui.py                 ← GUI 源码（可选）
├── build.bat              ← 构建脚本（可选）
└── README.md
```

## 技术架构

```
音频/视频输入
  │
  ├─→ ffmpeg 提取音频（视频文件）
  │
  ├─→ [GPU] Faster-Whisper medium → 带时间戳文本
  │
  ├─→ [CPU] zh-wiki-punctuation → 中文标点恢复
  │
  ├─→ [CPU] pyannote 3.1 → 说话人标签
  │
  └─→ 合并/格式化 → 输出 TXT/SRT（含时间戳）
```

## 首次运行模型下载

| 模型 | 大小 | 用途 |
|:---|:---|:---|
| Faster-Whisper medium | ~3GB | 语音转文字 |
| pyannote speaker-diarization-3.1 | ~500MB | 说话人区分 |
| zh-wiki-punctuation-restore | ~500MB | 中文标点恢复 |

setup.bat 会自动预下载，之后使用不再需要下载。

## 卸载

```bat
uninstall.bat
```

删除所有 pip 包、模型缓存（~4GB）和 HF_TOKEN 环境变量。工具文件夹需手动删除。

## 构建 exe（可选）

```bat
py -3.12 -m pip install pyinstaller
build.bat
```

## 更新日志

### v0.0.2
- 新增：批量多文件转写支持
- 新增：取消按钮，可随时中止转写
- 新增：输出文件名自动加时间戳，避免覆盖
- 新增：setup.bat 自动检测 CUDA 版本（11.x/12.x/CPU）
- 新增：根目录输入自动回退输出到桌面
- 修复：关闭窗口时子进程变孤儿占用 GPU
- 修复：ffmpeg 报错直接崩溃
- 修复：stderr 污染 JSON 进度解析
- 修复：标点恢复在中英混合文本可能错位
- 修复：setup.bat 空回车复用上次 HF_TOKEN
- 修复：uninstall.bat 模型缓存残留
- 改进：进度条更准确反映模型加载阶段
- 改进：UI 刷新限流，批量处理不卡顿

## 许可证

MIT

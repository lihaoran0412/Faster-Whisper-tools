@echo off
chcp 65001 >nul
echo ===========================================
echo   语音转文字工具 - 环境安装 v0.0.2
echo ===========================================
echo.

cd /d "%~dp0"

:: Check Python
echo [0/7] Check Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found!
    echo.
    echo Please install Python 3.12 from:
    echo   https://www.python.org/downloads/release/python-3129/
    echo.
    echo Make sure "py" launcher is available after install.
    pause
    exit /b 1
)
py -3.12 --version

:: Check NVIDIA GPU and CUDA version
echo [0/7] Check NVIDIA GPU...
set PYTORCH_INDEX=https://download.pytorch.org/whl/cpu
set TORCH_VER=torch torchaudio
for /f "tokens=*" %%i in ('py -3.12 -c "import subprocess,re;r=subprocess.run(['nvidia-smi'],capture_output=True,text=True);m=re.search(r'CUDA Version:\s*(\d+)\.',r.stdout);print(m.group(1) if m else '0')" 2^>nul') do set CUDA_MAJOR=%%i
if %CUDA_MAJOR% GEQ 12 (
    echo   Detected CUDA %CUDA_MAJOR%.x, using PyTorch cu121
    set PYTORCH_INDEX=https://download.pytorch.org/whl/cu121
    set TORCH_VER=torch==2.5.1 torchaudio==2.5.1
) else if %CUDA_MAJOR% GEQ 11 (
    echo   Detected CUDA %CUDA_MAJOR%.x, using PyTorch cu118
    set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
    set TORCH_VER=torch==2.5.1 torchaudio==2.5.1
) else (
    echo [WARN] No CUDA-capable GPU detected or driver too old.
    echo        Please install NVIDIA drivers from https://www.nvidia.com/drivers
    echo        You can continue with CPU, but transcription will be very slow.
)

:: Set HF token (user must provide their own)
echo.
echo ===========================================
echo   IMPORTANT: HuggingFace Token Required
echo ===========================================
echo.
echo To download pyannote models, you need a HuggingFace token.
echo If you already have one, enter it below.
echo If not:
echo   1. Register at https://huggingface.co/join
echo   2. Create token at https://huggingface.co/settings/tokens
echo   3. Accept model terms (see README)
echo.
set HF_TOKEN_INPUT=
set /p HF_TOKEN_INPUT="Enter your HF token (or press Enter to skip): "
if "%HF_TOKEN_INPUT%"=="" (
    echo   Skipped. You can set it later with:
    echo     setx HF_TOKEN your_token_here
) else (
    setx HF_TOKEN %HF_TOKEN_INPUT% >nul 2>&1
    set HF_TOKEN=%HF_TOKEN_INPUT%
    echo   Token saved.
)

set MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
set HF_ENDPOINT=https://hf-mirror.com
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

echo.
echo ===========================================
echo   Step 1-5: Install Python packages
echo ===========================================

echo [1/7] PyTorch (%PYTORCH_INDEX%)...
py -3.12 -m pip install %TORCH_VER% --index-url %PYTORCH_INDEX%

echo [2/7] cuDNN 8.9...
py -3.12 -m pip install nvidia-cudnn-cu12==8.9.7.29 -i %MIRROR%

echo [3/7] Core packages...
py -3.12 -m pip install faster-whisper transformers soundfile numpy huggingface-hub -i %MIRROR%

echo [4/7] pyannote.audio...
py -3.12 -m pip install pyannote.audio -i %MIRROR%

echo [5/7] GUI...
py -3.12 -m pip install tkinterdnd2 -i %MIRROR%

echo.
echo ===========================================
echo   Step 6/7: Verify packages (import only)
echo ===========================================

echo Checking PyTorch CUDA...
py -3.12 -c "import torch; print('  CUDA available:', torch.cuda.is_available())"

echo Checking faster-whisper...
py -3.12 -c "from faster_whisper import WhisperModel; print('  OK')"

echo Checking pyannote (import only)...
py -3.12 -c "import pyannote.audio; print('  OK')"

echo Checking transformers...
py -3.12 -c "from transformers import pipeline; print('  OK')"

echo Checking soundfile...
py -3.12 -c "import soundfile; print('  OK')"

echo Checking tkinterdnd2...
py -3.12 -c "import tkinterdnd2; print('  OK')"

echo.
echo ===========================================
echo   Step 7/7: Pre-download models (~4GB)
echo ===========================================
echo.
echo This may take 10-30 minutes. One-time only.
echo.

echo [A] Faster-Whisper medium (~3GB)...
py -3.12 -c "from faster_whisper import WhisperModel; m=WhisperModel('medium', device='cpu', compute_type='auto'); print('  Done')"
if errorlevel 1 (
    echo   [WARN] Download failed. Check network or try again later.
)

echo.
echo [B] pyannote models (~500MB)...
echo   NOTE: Requires accepting HF model terms first!
py -3.12 -c "from pyannote.audio import Pipeline; p=Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', token=os.environ['HF_TOKEN']); print('  Done')"
if errorlevel 1 (
    echo   [WARN] Download failed. You MUST accept these on huggingface.co first:
    echo     1. https://hf.co/pyannote/speaker-diarization-3.1
    echo     2. https://hf.co/pyannote/segmentation-3.0
    echo     3. https://hf.co/pyannote/speaker-diarization-community-1
    echo   Then re-run: setup.bat
)

echo.
echo [C] Punctuation model (~500MB)...
py -3.12 -c "from transformers import pipeline; p=pipeline('token-classification', model='p208p2002/zh-wiki-punctuation-restore'); print('  Done')"
if errorlevel 1 (
    echo   [WARN] Download failed. Check network or try again later.
)

echo.
echo ===========================================
echo   INSTALLATION COMPLETE
echo ===========================================
echo.
echo Files in this directory:
echo   transcribe_tool.exe   - Double-click to run
echo   pipeline.py           - Backend pipeline
echo   ffmpeg.exe            - Audio/video decoder
echo.
echo   Double-click: transcribe_tool.exe
echo ===========================================
pause

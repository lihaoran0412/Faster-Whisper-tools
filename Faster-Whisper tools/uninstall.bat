@echo off
chcp 65001 >nul
echo ===========================================
echo   语音转文字工具 - 卸载
echo ===========================================
echo.

echo This will remove:
echo   - Python packages installed by setup.bat
echo   - Downloaded models (~4GB)
echo   - HF_TOKEN environment variable
echo.
echo WARNING: torch and transformers are shared packages.
echo If other projects use them, they will also be removed.
echo.
echo The tool folder itself will NOT be deleted.
echo.
set /p CONFIRM="Continue? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo [1/4] Removing Python packages...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo   Python 3.12 not found, skipping pip uninstall.
    echo   If Python is installed as a different version, manually run:
    echo     pip uninstall faster-whisper pyannote.audio transformers soundfile tkinterdnd2 torch torchaudio
) else (
    py -3.12 -m pip uninstall -y faster-whisper pyannote.audio transformers soundfile tkinterdnd2 nvidia-cudnn-cu12 torch torchaudio 2>nul
    echo   Done
)

echo.
echo [2/4] Removing model cache...
if exist "%USERPROFILE%\.cache\faster-whisper" (
    rmdir /s /q "%USERPROFILE%\.cache\faster-whisper"
    echo   Removed: faster-whisper cache
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--speaker-diarization-3.1" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--speaker-diarization-3.1"
    echo   Removed: pyannote diarization model
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--segmentation-3.0" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--segmentation-3.0"
    echo   Removed: pyannote segmentation model
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--speaker-diarization-community-1" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--speaker-diarization-community-1"
    echo   Removed: pyannote community model
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--p208p2002--zh-wiki-punctuation-restore" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--p208p2002--zh-wiki-punctuation-restore"
    echo   Removed: punctuation model
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--wespeaker-voxceleb-resnet34-LM" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--pyannote--wespeaker-voxceleb-resnet34-LM"
    echo   Removed: wespeaker model
)
if exist "%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-medium" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-medium"
    echo   Removed: faster-whisper hub cache
)

echo.
echo [3/4] Removing HF_TOKEN...
reg delete HKCU\Environment /v HF_TOKEN /f 2>nul
if errorlevel 1 (
    echo   HF_TOKEN was not set or already removed.
) else (
    echo   Removed: HF_TOKEN
)

echo.
echo [4/4] Cleanup complete.
echo.
echo To fully remove the tool, manually delete this folder:
echo   %~dp0
echo.
echo ===========================================
echo   Uninstall complete.
echo ===========================================
pause

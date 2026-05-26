@echo off
echo [1/2] Build exe...
py -3.12 -m PyInstaller --noconsole --onefile --name transcribe_tool --hidden-import tkinterdnd2 --hidden-import soundfile gui.py
echo [2/2] Copy...
copy /Y "dist\transcribe_tool.exe" transcribe_tool.exe
rmdir /s /q build dist 2>nul
del transcribe_tool.spec 2>nul
echo Done!
pause

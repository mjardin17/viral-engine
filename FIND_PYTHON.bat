@echo off
echo Searching for Python on this computer...
echo.
where python 2>nul && echo FOUND: python in PATH
where py 2>nul && echo FOUND: py launcher
dir /b "C:\Users\jjard\AppData\Local\Programs\Python\" 2>nul
dir /b "C:\Users\jjard\jjclaudevideobot\Scripts\python.exe" 2>nul && echo FOUND: venv jjclaudevideobot
echo.
echo Done. Take a screenshot and show Claude.
pause

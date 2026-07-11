@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
echo Using Python: %PYTHON%
echo Installing packages...
"%PYTHON%" -m pip install google-auth-oauthlib google-api-python-client --quiet
echo Starting uploader...
"%PYTHON%" easy_youtube_uploader.py
pause

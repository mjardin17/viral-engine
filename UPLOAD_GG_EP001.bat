@echo off
echo ============================================
echo  EMPIRE OS — Upload GG EP001 to YouTube
echo ============================================
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo [1/3] Installing Google API libraries...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -m pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client --quiet

echo.
echo [2/3] Getting YouTube token for Gods and Glory...
echo When browser opens — sign in as godsandgloryai@gmail.com
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe get_token_gg.py

echo.
echo [3/3] Uploading GG EP001...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe channel_uploader.py --channel gg --episodes GG_EP001 --privacy public

echo.
echo ============================================
echo  DONE — check above for YouTube URL
echo ============================================
pause

@echo off
cd /d C:\Users\jjard\claude\video-bot-pipeline
echo === Empire OS: upload LO_EP001 to YouTube (lo) ===
"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe" channel_uploader.py --channel lo --episodes LO_EP001
if errorlevel 1 (
  echo Upload failed or aborted - social publish NOT run.
  pause
  exit /b 1
)
echo === YouTube done - auto-posting social clips ===
"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe" social_clips\auto_publisher.py --episode LO_EP001 --channel lo
pause

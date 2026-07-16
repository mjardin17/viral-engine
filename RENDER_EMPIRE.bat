@echo off
echo Empire OS Render — Boss Tool
echo ============================
echo Usage: Pass args directly to empire_render.py
echo Example: RENDER_EMPIRE.bat --channel GG --episode GG_EP012
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0empire_render.py" %*
if errorlevel 1 (
  echo.
  echo RENDER FAILED — check output above
  pause
) else (
  echo.
  echo RENDER COMPLETE
  pause
)

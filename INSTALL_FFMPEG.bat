@echo off
cd /d "%~dp0"
echo.
echo ====================================
echo  Installing ffmpeg (no admin needed)
echo  Downloads directly here
echo ====================================
echo.

set FFBIN=%~dp0ffmpeg_bin

if exist "%FFBIN%\ffmpeg.exe" (
    echo ffmpeg already installed!
    echo Location: %FFBIN%\ffmpeg.exe
    goto :done
)

echo Step 1: Downloading ffmpeg (80MB, takes 1-3 min)...
powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg_dl.zip' -UseBasicParsing"

if not exist ffmpeg_dl.zip (
    echo.
    echo DOWNLOAD FAILED. Try this URL manually:
    echo https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo Save it to: %~dp0ffmpeg_dl.zip
    echo Then run this bat again.
    pause
    exit /b 1
)

echo Step 2: Extracting...
mkdir "%FFBIN%" 2>nul
powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'ffmpeg_dl.zip' -DestinationPath 'ffmpeg_extract_temp' -Force"

echo Step 3: Copying ffmpeg.exe and ffprobe.exe...
for /d %%D in (ffmpeg_extract_temp\*) do (
    if exist "%%D\bin\ffmpeg.exe" (
        copy "%%D\bin\ffmpeg.exe" "%FFBIN%\ffmpeg.exe" >nul
        copy "%%D\bin\ffprobe.exe" "%FFBIN%\ffprobe.exe" >nul
    )
)

echo Step 4: Cleaning up...
del ffmpeg_dl.zip 2>nul
rmdir /s /q ffmpeg_extract_temp 2>nul

:done
echo.
if exist "%FFBIN%\ffmpeg.exe" (
    echo SUCCESS — ffmpeg is ready.
    echo.
    echo Now double-click render_all_45min.bat to start rendering.
) else (
    echo ERROR: Something went wrong. ffmpeg.exe not found after install.
)
echo.
pause

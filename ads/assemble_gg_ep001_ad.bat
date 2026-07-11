@echo off
REM ============================================================
REM Gods & Glory EP001 Ad — Final Assembly
REM Combines 4 video clips + voiceover into GG_EP001_ad.mp4
REM Run this from the ads\ folder after downloading the files
REM ============================================================

setlocal

REM ---- OUTPUT LOCATION -----------------------------------------------
set OUT=%~dp0GG_EP001_ad.mp4
set TMPDIR=%~dp0tmp_concat

REM ---- SOURCE FILES (CDN URLs — will be downloaded) ------------------
REM CLIP 1: Lone Spartan at Thermopylae (8s)
set URL_V1=https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_143653_3976f7ad-5254-4b85-907d-7f99fbcdf2a9.mp4
REM CLIP 2: Persian army charging (8s)
set URL_V2=https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155756_9d32df9a-107f-49e5-8a4e-f2fe6790f6ca.mp4
REM CLIP 3: Spartan phalanx formation (8s)
set URL_V3=https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155758_8579988b-6f97-4239-ade3-df59692c6591.mp4
REM CLIP 4: Gods & Glory temple reveal (8s)
set URL_V4=https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155759_80eaa4fa-3bef-4985-a573-190cf78e4e96.mp4
REM AUDIO: Roman voice narration (30.5s)
set URL_AUDIO=https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_143611_cd166e82-5aaf-4735-9dce-36f3eb9adb3a.wav

echo.
echo Gods ^& Glory EP001 Ad Assembler
echo =================================
echo.

REM ---- CHECK FFMPEG --------------------------------------------------
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: ffmpeg not found. Install from https://ffmpeg.org/download.html
    exit /b 1
)

REM ---- CREATE TEMP DIR -----------------------------------------------
if not exist "%TMPDIR%" mkdir "%TMPDIR%"

REM ---- DOWNLOAD CLIPS ------------------------------------------------
echo Downloading clips...
curl -L -o "%TMPDIR%\clip1.mp4" "%URL_V1%"
curl -L -o "%TMPDIR%\clip2.mp4" "%URL_V2%"
curl -L -o "%TMPDIR%\clip3.mp4" "%URL_V3%"
curl -L -o "%TMPDIR%\clip4.mp4" "%URL_V4%"
curl -L -o "%TMPDIR%\narration.wav" "%URL_AUDIO%"

REM ---- WRITE CONCAT LIST ---------------------------------------------
echo file 'clip1.mp4' > "%TMPDIR%\concat.txt"
echo file 'clip2.mp4' >> "%TMPDIR%\concat.txt"
echo file 'clip3.mp4' >> "%TMPDIR%\concat.txt"
echo file 'clip4.mp4' >> "%TMPDIR%\concat.txt"

REM ---- CONCATENATE CLIPS ---------------------------------------------
echo Concatenating video clips...
ffmpeg -y -f concat -safe 0 -i "%TMPDIR%\concat.txt" -c copy "%TMPDIR%\combined_video.mp4"

REM ---- MIX AUDIO IN --------------------------------------------------
echo Adding narration audio...
ffmpeg -y ^
  -i "%TMPDIR%\combined_video.mp4" ^
  -i "%TMPDIR%\narration.wav" ^
  -map 0:v -map 1:a ^
  -c:v libx264 -preset fast -crf 18 ^
  -c:a aac -b:a 192k ^
  -shortest ^
  "%OUT%"

REM ---- DONE ----------------------------------------------------------
echo.
if exist "%OUT%" (
    echo SUCCESS: %OUT%
    for %%F in ("%OUT%") do echo Size: %%~zF bytes
) else (
    echo ERROR: Output file not created. Check ffmpeg logs above.
    exit /b 1
)

REM ---- CLEANUP -------------------------------------------------------
rmdir /s /q "%TMPDIR%"

echo.
echo Upload "%OUT%" to YouTube as a channel ad or pre-roll.
echo.
pause

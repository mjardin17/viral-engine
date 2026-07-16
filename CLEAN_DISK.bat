@echo off
title EMPIRE OS — Safe Disk Cleanup
echo.
echo [1/6] Clearing output\ (9.2 GB temp render files)...
if exist "%~dp0output" (
    rd /s /q "%~dp0output"
    mkdir "%~dp0output"
    echo Done.
) else (
    echo output\ not found, skipping.
)

echo [2/6] Clearing renders\_archive\...
if exist "%~dp0renders\_archive" (
    rd /s /q "%~dp0renders\_archive"
    echo Done.
) else (
    echo _archive not found, skipping.
)

echo [3/6] Clearing renders\_backups\...
if exist "%~dp0renders\_backups" (
    rd /s /q "%~dp0renders\_backups"
    echo Done.
) else (
    echo _backups not found, skipping.
)

echo [4/6] Clearing renders\_test_work\...
if exist "%~dp0renders\_test_work" (
    rd /s /q "%~dp0renders\_test_work"
    echo Done.
) else (
    echo _test_work not found, skipping.
)

echo [5/6] Clearing renders\thermopylae_doc\ (old test renders)...
if exist "%~dp0renders\thermopylae_doc" (
    rd /s /q "%~dp0renders\thermopylae_doc"
    echo Done.
) else (
    echo thermopylae_doc not found, skipping.
)

echo [6/6] Clearing empire-os-hub\node_modules\ (250 MB)...
if exist "%~dp0empire-os-hub\node_modules" (
    rd /s /q "%~dp0empire-os-hub\node_modules"
    echo Done.
) else (
    echo node_modules not found, skipping.
)

echo.
echo ============================================================
echo   CLEANUP COMPLETE!
echo   output/, test renders, backups, node_modules cleared.
echo.
echo   NEXT: Delete Ollama models for 8.7 GB more:
echo   Run: ollama list   then: ollama rm [model-name]
echo   OR delete contents of: C:\Users\jjard\.ollama\models\blobs\
echo.
echo   NEXT: Run Windows Disk Cleanup for 1.2 GB temp files:
echo   Press Win+R, type: cleanmgr, press Enter
echo.
echo   NEXT: Investigate Downloads (16 GB) - open Downloads,
echo   sort by Size desc, scroll past JPEGs to find big files.
echo ============================================================
pause

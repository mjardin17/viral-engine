@echo off
title Empire OS — Book Pipeline
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
cd /d C:\Users\jjard\claude\video-bot-pipeline

:menu
echo.
echo  ==========================================
echo   EMPIRE OS — BOOK PIPELINE
echo   research - generate - package - distribute
echo  ==========================================
echo  Commands:
echo  1. Research niches
echo  2. Generate a book
echo  3. Package EPUB
echo  4. Distribute
echo  5. Status
echo  6. Install dependencies
echo  7. Exit
echo.
set CMD=
set /p CMD="Enter command number: "

if "%CMD%"=="1" goto research
if "%CMD%"=="2" goto generate
if "%CMD%"=="3" goto package
if "%CMD%"=="4" goto distribute
if "%CMD%"=="5" goto status
if "%CMD%"=="6" goto deps
if "%CMD%"=="7" goto end
echo  Invalid choice — enter 1-7.
goto menu

:research
"%PYTHON%" book_pipeline.py research
goto menu

:generate
set NICHE=
set BTITLE=
set /p NICHE="Niche (e.g. personal finance): "
set /p BTITLE="Book title: "
if "%NICHE%"=="" (echo  Niche is required. & goto menu)
if "%BTITLE%"=="" (echo  Title is required. & goto menu)
"%PYTHON%" book_pipeline.py generate --niche "%NICHE%" --title "%BTITLE%"
goto menu

:package
set BTITLE=
set /p BTITLE="Book title to package: "
if "%BTITLE%"=="" (echo  Title is required. & goto menu)
"%PYTHON%" book_pipeline.py package --title "%BTITLE%"
goto menu

:distribute
set BTITLE=
set /p BTITLE="Book title to distribute: "
if "%BTITLE%"=="" (echo  Title is required. & goto menu)
"%PYTHON%" book_pipeline.py distribute --title "%BTITLE%"
goto menu

:status
"%PYTHON%" book_pipeline.py status
goto menu

:deps
echo  Installing: requests, google-generativeai, ebooklib ...
"%PYTHON%" -m pip install requests google-generativeai ebooklib
goto menu

:end
echo  Done.

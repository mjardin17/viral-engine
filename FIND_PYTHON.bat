@echo off
echo Searching for Python installs...
echo.
echo == LOCALAPPDATA\Programs\Python ==
dir "%LOCALAPPDATA%\Programs\Python\" 2>nul || echo  not found

echo.
echo == C:\Program Files\Python* ==
dir "C:\Program Files\Python*" /b 2>nul || echo  not found

echo.
echo == C:\Python* ==
dir "C:\Python*" /b 2>nul || echo  not found

echo.
echo == PATH python ==
where python 2>nul || echo  not in PATH

echo.
echo == PATH python3 ==
where python3 2>nul || echo  not in PATH

echo.
pause

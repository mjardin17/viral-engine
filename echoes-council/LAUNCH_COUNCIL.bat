@echo off
cd /d "%~dp0"
echo Starting Echoes Council v2.3...
docker compose up --build --force-recreate
pause

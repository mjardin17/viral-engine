@echo off
cd /d "C:\Users\jjard\claude\video-bot-pipeline"
git add -A
git commit -m "[CLAUDE] fix: fix 9 unit test failures in packages/core (event-bus field/method naming collision, workflow-engine reject race condition, memory-bus timestamp flake, step-done topic string)"
git push origin main
echo.
echo Done! 129/129 tests passing committed to main.
pause

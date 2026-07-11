@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Empire OS — Provider verification tests
REM  Run AFTER restarting the server.
REM  Each curl hits a different endpoint to confirm routing works.
REM ═══════════════════════════════════════════════════════════════

echo.
echo [1/5] Checking Ollama is up...
curl -s http://localhost:11434/api/tags | findstr "models"
echo.

echo [2/5] Listing all Empire OS providers...
curl -s http://localhost:3001/providers
echo.
echo.

echo [3/5] Routing test — cost strategy (should pick Ollama)...
curl -s -X POST http://localhost:3001/empire-assistant/ai/complete ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: OLLAMA_OK\"}],\"strategy\":\"cost\",\"callerId\":\"verify-script\"}"
echo.
echo.

echo [4/5] Routing test — quality strategy (should pick Claude or Gemini)...
curl -s -X POST http://localhost:3001/empire-assistant/ai/complete ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: CLOUD_OK\"}],\"strategy\":\"quality\",\"callerId\":\"verify-script\"}"
echo.
echo.

echo [5/5] Routing test — local-only strategy (must use Ollama only)...
curl -s -X POST http://localhost:3001/empire-assistant/ai/complete ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: LOCAL_OK\"}],\"strategy\":\"local-only\",\"callerId\":\"verify-script\"}"
echo.
echo.

echo Done. Check the 'provider' field in each response above.
echo   cost     → should show "ollama"
echo   quality  → should show "anthropic" or "google"
echo   local-only → should show "ollama"
pause

# Video Pipeline Agent

Autonomous agent that monitors and executes render jobs from `MISSION_BOARD.json`.

## What it does

1. **Monitors** `MISSION_BOARD.json` for pending render missions
2. **Posts status** to the Buzz relay's #video-pipeline channel in real-time
3. **Executes renders** using `empire_render.py`
4. **Reports results** (success/failure) back to Buzz
5. **Runs continuously** — polls every 30 seconds

## How to run

### Option 1: Batch file (easiest)
```
START_VIDEO_PIPELINE_AGENT.bat
```

### Option 2: PowerShell
```powershell
$env:BUZZ_PRIVATE_KEY = "31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04"
$env:BUZZ_RELAY_URL = "ws://localhost:3000"

python agents/video_pipeline_agent.py
```

### Option 3: Manual Python
```bash
cd C:\Users\jjard\claude\video-bot-pipeline
python -m agents.video_pipeline_agent
```

## Prerequites

- ✅ Buzz relay running on `localhost:3000`
- ✅ `MISSION_BOARD.json` in repo root (auto-created if missing)
- ✅ `empire_render.py` available in repo root
- ✅ Python 3.14+ installed

## Channel: #video-pipeline

Agent posts to Buzz channel `#video-pipeline`:
- 🚀 Render start notifications
- ✅ Completion confirmations
- ❌ Failure alerts with error details
- ⚠️ Agent health status

Humans can react to messages, approve renders, or post commands to the channel (future extension).

## Mission Board Format

Agents expect `MISSION_BOARD.json` with structure:

```json
{
  "missions": [
    {
      "id": "render-gg-ep001",
      "title": "Render GG EP001",
      "channel": "GG",
      "episode": "001",
      "status": "pending",
      "priority": 1,
      "created_at": "2026-08-09T13:00:00Z"
    }
  ]
}
```

Agent marks missions as `completed` after successful render.

## Logs

Agent outputs:
- Console: local status + errors
- Buzz channel: all human-facing messages
- No separate log files (all in Buzz audit trail)

## Future extensions

- [ ] Agent can be commanded from Buzz channel ("render GG EP002")
- [ ] Integration with Council bots for quality checks
- [ ] Auto-upload to YouTube after render
- [ ] Failure retry logic with exponential backoff

EMPIRE OS AGENT — READ FIRST
Repo: C:\Users\jjard\claude\video-bot-pipeline\
Python: C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
Memory files to read before acting:
  1. CLAUDE.md — master rules and project state
  2. AGENT_MEMORY.md — architecture and what's been built
  3. MISSION_BOARD.json — current mission queue (your mission: m004)

---

MISSION m004: Build render_orchestrator.py

Build a parallel episode render orchestrator for Empire OS.

## What it must do

- Accept a list of episodes and a worker count (default N=2)
- Launch N simultaneous auto_render.py subprocesses
- Each worker pulls the next episode from the queue when it finishes
- Print live status: which worker is on which episode, % done, ETA
- When an episode finishes: log it to render_log.json with file size + timestamp
- On failure: log the error, skip that episode, keep other workers running
- When ALL renders finish: print a summary (passed / failed / skipped)

## Interface

```
python render_orchestrator.py --episodes GG_EP012,GG_EP013,GG_EP014 --workers 2
python render_orchestrator.py --season 3 --channel gg --workers 3
python render_orchestrator.py --pending   # reads MISSION_BOARD.json for pending renders
```

## Key paths

- auto_render.py: C:\Users\jjard\claude\video-bot-pipeline\auto_render.py
- Music: C:\Users\jjard\claude\video-bot-pipeline\music\battle_epic.mp3
- Output: C:\Users\jjard\claude\video-bot-pipeline\renders\
- Log: C:\Users\jjard\claude\video-bot-pipeline\render_log.json
- Python: C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

## Rules

- Must NOT modify auto_render.py
- Must NOT run more than 3 workers (RAM limit)
- Use subprocess.Popen (non-blocking) — NOT subprocess.run
- Typed, modular, documented Python 3.14
- Save to: C:\Users\jjard\claude\video-bot-pipeline\render_orchestrator.py

## When done

Confirm: file saved, syntax check passes, report what you built.
Update MISSION_BOARD.json: set m004 status to "complete", result = file path.

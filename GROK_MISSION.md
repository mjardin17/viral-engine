EMPIRE OS AGENT — READ FIRST
Repo: C:\Users\jjard\claude\video-bot-pipeline\
Python: C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
Memory files to read before acting:
  1. CLAUDE.md — master rules and project state
  2. AGENT_MEMORY.md — architecture and what's been built
  3. MISSION_BOARD.json — current mission queue (your missions: m003, m007)

---

MISSION m003: Re-render broken/stub GG episodes
MISSION m007: Render IL_EP001 (Iron Legends first episode)

## m003 — Re-render these GG episodes

Episodes to fix:
- GG_EP006 (Pearl Harbor) — BROKEN. 21 of 24 clips are 0KB. Delete existing clips and re-render from scratch.
- GG_EP008, GG_EP009, GG_EP010, GG_EP011 — STUBS. Under 18 min each. Scripts exist in prompts/gods_glory/. Re-render.

Run each one:
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP006 --music music\battle_epic.mp3
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP008 --music music\battle_epic.mp3
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP009 --music music\battle_epic.mp3
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP010 --music music\battle_epic.mp3
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP011 --music music\battle_epic.mp3
```

For EP006: first delete broken clips:
- Delete all files in: output\GG_EP006\clips\ that are 0 bytes
- Then run auto_render.py — it will regenerate missing clips

## m007 — Render IL_EP001

Script lives at: prompts\ (look for IL_EP001.json or similar)
Run:
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode IL_EP001 --music music\battle_epic.mp3
```

## After each render

Run ffprobe to verify duration:
```
ffmpeg_bin\ffprobe.exe -v error -show_entries format=duration -of csv=p=0 renders\GG_EP006_final.mp4
```

Expected: >2700 seconds (45 min). Flag anything under that.

## Report back

For each episode: DONE [file size] [duration] or BLOCKED [error].
Update MISSION_BOARD.json: m003 and m007 to "complete" or "blocked" with details.

## Critical rules

- Run from: C:\Users\jjard\claude\video-bot-pipeline\
- NEVER use token.pickle for anything
- Do NOT modify auto_render.py
- Do NOT upload anything — renders only

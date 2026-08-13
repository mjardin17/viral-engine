# CLAUDE CODE CLEANUP MISSION
**Target Agent:** Claude Code (runs on Josh's machine)  
**Priority:** CRITICAL  
**Mission ID:** cleanup_bullshit_001

---

## CONTEXT BLOCK (READ FIRST)
```
Repo: C:\Users\jjard\claude\video-bot-pipeline\
Python: C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
Current state:
  - 70+ render/upload/pipeline scripts scattered across repo root
  - Multiple duplicate renderers: empire_render.py, render_gg_v3.py, render.py, render_ml_ep001_win.py
  - Multiple duplicate uploaders: channel_uploader.py, easy_youtube_uploader.py, upload_gg_full.py
  - LO_EP001 render is broken (4 identical scenes repeating)
  - Need: ONE canonical render path, ONE canonical uploader, clean repo

Main goal: Consolidate all render/upload logic into ONE path, delete dead code, fix broken render.
```

---

## MISSION: DELETE ALL THE BULLSHIT

### PHASE 1: AUDIT & IDENTIFY (no deletion yet)

**File scan:** Find all render/upload/pipeline scripts in repo root:
```bash
ls -la *.py | grep -E "render|upload|pipeline|auto_|watch_|generate_"
```

Expected to find (DELETE after confirming):
- `render_gg_v3.py` — OLD GG renderer, superseded by empire_render.py
- `render_ml_ep001_win.py` — OLD ML episode render, obsolete
- `render.py` — OLD generic renderer
- `easy_youtube_uploader.py` — OLD uploader, replaced by channel_uploader.py
- `upload_gg_full.py` — OLD GG-specific uploader, redundant
- `upload_watcher.py` — OLD auto-upload watcher
- `auto_upload_watcher.py` — NEWER auto-upload watcher (also broken)
- `auto_render.py` — runner script (CHECK if it's still needed or can be replaced by empire_render.py --multi-channel)
- `empire_runner.py` — OLD runner
- `pipeline_run.py` — OLD runner
- `watch_and_save.py` — OLD watcher
- `_append_helper.py` — helper script (CHECK if used)
- `setup_wizard.py` — onboarding (KEEP? only if Josh explicitly uses it)

**Confirm current production scripts (DO NOT DELETE):**
- ✅ `empire_render.py` — CANONICAL renderer (all channels)
- ✅ `channel_uploader.py` — CANONICAL uploader (all channels)
- ✅ `orchestrator/empire_orchestrator.py` — CANONICAL task dispatcher
- ✅ `council/council.py` + `council/bots/*.py` — CANONICAL quality checker (14 bots)

---

### PHASE 2: VERIFY NO ACTIVE DEPENDENCIES

Before deleting any script:
1. **Search for imports:** `grep -r "from render import\|import render_gg_v3\|import easy_youtube" . --include="*.py" | grep -v ".pyc"`
   - If found anywhere OUTSIDE the deleted file, STOP and report
2. **Search for subprocess calls:** `grep -r "render_gg_v3.py\|easy_youtube_uploader.py\|upload_watcher.py" . --include="*.py" --include="*.bat" --include="*.md"`
   - If found, STOP and report (it means something is still calling it)
3. **Check .bat files:** Look in `*.bat` files for references to deleted scripts
   - Example: if `RENDER_EMPIRE.bat` calls `python render_gg_v3.py`, that's a dependency

**Report format:**
```
AUDIT RESULTS:
- Scripts to delete: [list with reason]
- Active dependencies found: [if any, STOP here]
- Safe to proceed: YES/NO
```

---

### PHASE 3: DELETE DEAD CODE (only if Phase 2 says "Safe to proceed: YES")

**Delete these files:**
```bash
rm -f render_gg_v3.py
rm -f render_ml_ep001_win.py
rm -f render.py
rm -f easy_youtube_uploader.py
rm -f upload_gg_full.py
rm -f upload_watcher.py
rm -f auto_upload_watcher.py
rm -f empire_runner.py
rm -f pipeline_run.py
rm -f watch_and_save.py
rm -f _append_helper.py
```

**Do NOT delete yet:**
- `auto_render.py` — need to confirm it's not active (CHECK MISSION_BOARD.json for references)
- `setup_wizard.py` — might be used for onboarding (ask Josh or skip)

**After deletion:**
```bash
git status
```
Should show ~12 deleted files. Do NOT commit yet — wait for Josh to approve.

---

### PHASE 4: VERIFY empire_render.py CAN HANDLE EVERYTHING

Check that `empire_render.py` supports:
- ✅ All 5 channels: `--channel GG|LO|IL|ED|EOE`
- ✅ Multiple episodes: `--episodes GG_EP001,GG_EP002` or `--episodes all`
- ✅ Dry-run mode: `--dry-run`
- ✅ Council evaluation: automatic after render
- ✅ Music selection: automatic from music/ or explicit `--music <path>`

**Verify lines in empire_render.py:**
```bash
grep -n "argparse\|--channel\|--episode\|--dry-run" empire_render.py | head -20
```

Expected to find: argument parser with all flags above. If missing, report BLOCKED.

---

### PHASE 5: DELETE ALL OLD TRASH RENDERS

**Old broken/test renders to delete:**
```bash
# Find all renders EXCEPT the current ones
ls -lh renders/
# Delete:
rm -rf renders/LO_EP001_HIGGSFIELD_final.mp4  # broken (4 scenes repeating)
rm -rf renders/GG_EP001-EP005_old/  # if exists
rm -rf renders/*_test_*.mp4
rm -rf renders/*_draft_*.mp4
rm -rf output/  # working directory trash
# Keep only:
  - renders/gods_glory/GG_EP*.mp4 (the good finals)
  - renders/little_olympus/LO_EP*.mp4 (only if they're actually good)
  - renders/iron_legends/IL_EP*.mp4
```

**Verify what to keep:**
```bash
ffprobe renders/little_olympus/LO_EP001_final.mp4 -show_entries format=duration
```
- If duration < 2700 seconds (45 min) → trash it (incomplete render)
- If duration >= 2700 → might be good, but visually inspect first

**Report format:**
```
Deleted trash renders:
- LO_EP001_HIGGSFIELD_final.mp4 (broken)
- [any others found]

Kept renders:
- [list good ones with duration]
```

---

### PHASE 6: FIX BROKEN LO_EP001 RENDER (or skip if deleted)

**If LO_EP001_final.mp4 in renders/little_olympus/ looks good:**
Check if it has all 24 unique scenes or just 4 repeating:
```bash
ffprobe renders/little_olympus/LO_EP001_final.mp4 -show_entries format=duration
# If duration too short, delete it
rm renders/little_olympus/LO_EP001_final.mp4
```

**Recommendation:** Use credit-stretching system to re-render properly
```bash
python scene_classifier.py prompts/little_olympus/LO_EP001.json
python episode_credit_planner.py prompts/little_olympus/LO_EP001.json --budget 50
```
This will route 18 scenes to free (WikiArt + Ken Burns), 6 to Higgsfield — ensuring all 24 scenes are unique.

**Report:** "EP001 trash deleted, ready for clean re-render via credit-stretching system"

---

### PHASE 6: UPDATE DOCUMENTATION

After cleanup, update these files:
1. **CLAUDE.md** — remove references to old renderers, confirm empire_render.py is canonical
2. **AGENT_MEMORY.md** — update rendering instructions to point to empire_render.py only
3. **README.md** (if exists) — simplify render instructions

---

## REPORT FORMAT (when done)

```
CLEANUP MISSION COMPLETE

Phase 1 (Audit):
- Total scripts found: N
- Safe to delete: N scripts
- Active dependencies: NONE / YES (list them)

Phase 2 (Verification):
- Status: SAFE TO PROCEED / BLOCKED

Phase 3 (Deletion):
- Deleted: [list of files]
- git status: N files deleted

Phase 4 (empire_render.py verification):
- Supports all channels: YES / NO
- Supports all flags: YES / NO / MISSING: [list]

Phase 5 (LO_EP001 fix):
- Root cause: [clips missing / assembly broken / other]
- Fix: [recommended next step]

Phase 6 (Documentation):
- Updated files: [list]

NEXT STEP:
- Run: git add -A && git commit -m "[CLAUDE_CODE] chore: delete 12 dead render/upload scripts"
- Then: git push (via PUSH_NOW.bat)
- Then: Josh approves and re-renders LO_EP001 using credit-stretching system
```

---

## EXECUTION CHECKLIST

- [ ] Phase 1: Audit complete, report dependencies
- [ ] Phase 2: Verify no active imports/calls to old scripts
- [ ] Phase 3: Delete dead files (DO NOT COMMIT YET)
- [ ] Phase 4: Confirm empire_render.py has all features
- [ ] Phase 5: Identify LO_EP001 issue and recommend fix
- [ ] Phase 6: Update docs
- [ ] Report: Final status and git commands for Josh to run

---

## CRITICAL RULES

1. **NO COMMITS UNTIL PHASE 2 PASSES** — only report findings, wait for Josh approval
2. **NO DELETION UNTIL DEPENDENCIES VERIFIED** — a broken grep means something still uses it
3. **PRESERVE MISSION_BOARD.json** — DO NOT edit it, only read it for dependency info
4. **REPORT BLOCKING ISSUES IMMEDIATELY** — if active dependencies found, stop and report
5. **DO NOT RENAME** — only delete (renames can leave broken imports behind)

---

## When complete, provide:
1. List of deleted files
2. git status output
3. LO_EP001 fix recommendation
4. Next commands for Josh to run

Ready to execute.

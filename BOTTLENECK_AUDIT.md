# Pipeline Bottleneck Audit
**Dated:** 2026-07-18 | **Model:** Claude Haiku

Systematic review of concurrency, parallelism, file I/O, API rate limiting, and architectural chokepoints.

---

## CRITICAL BOTTLENECKS (High Impact, Easy Fix)

### 1. **Scene Rendering Parallelism — MAX_PARALLEL_SCENES = 2** ⚠️ BLOCKING
**Location:** `empire_render.py` line 139  
**Impact:** High  
**Current:** Only 2 scenes render concurrently  
**Why it's a bottleneck:**
- 24-scene LO episode: 12 sequential passes (24 scenes ÷ 2 parallel)
- Each pass takes 10-30 seconds (image gen + Kokoro + encode)
- Total: 2-6 minutes just from serial bottleneck

**Root cause:** Set to 2 to avoid Pollinations rate-limit (1 req/sec). But we now have:
- Waterfall with 8 free image providers (Wikimedia, WikiArt, Openverse, Lexica, Gemini, Pollinations, AI Horde, Picsum)
- AI Router that spreads load
- FLUX/Kontext via FAL (parallel-safe)
- Gemini image (separate quota)

**Fix:** Increase to 4-6, route image-gen through AI Router to spread across providers

**Estimated gain:** 2-3x faster scene rendering (scenes/minute goes 12 → 30-40)

---

### 2. **Orchestrator Poll Interval — POLL_INTERVAL_SEC = 30** ⚠️ BLOCKING
**Location:** `orchestrator/empire_orchestrator.py` line 59  
**Impact:** High  
**Current:** Orchestrator polls MISSION_BOARD every 30 seconds  
**Why it's a bottleneck:**
- New render task queued at T=5 → not picked up until T=30
- 25-second latency before episode starts rendering
- Multi-episode batches serialize with 30s gaps between starts

**Fix options:**
- Reduce to 10 seconds (reasonable poll load)
- Implement callback/event-based triggering instead of poll (eliminates latency entirely)
- Run orchestrator as a daemon with inotify on MISSION_BOARD.json

**Estimated gain:** 25-second latency elimination per episode = 4-6 episodes/hour faster throughput

---

### 3. **Image Generation Not Batched** ⚠️ HIGH IMPACT
**Location:** `empire_render.py` fetch_scene_images() (sequential loop)  
**Impact:** High  
**Current:** Scenes fetch 4 images one-at-a-time
```python
for scene in scenes:
    for image_idx in range(4):
        fetch_image()  # one at a time
```

**Why it's a bottleneck:**
- 24 scenes × 4 images = 96 image fetches
- Each fetch: 1-2 seconds (Gemini/Pollinations)
- Total: 96-192 seconds just on sequential fetching

**Fix:** Batch the fetches
```python
all_fetches = []
for scene in scenes:
    for i in range(4):
        future = thread_pool.submit(fetch_image, ...)
        all_fetches.append(future)
# Wait for all to complete in parallel
wait(all_fetches)
```

**Estimated gain:** 3-4x faster (192s → 45-60s for 96 images with 4 workers)

---

## SECONDARY BOTTLENECKS (Medium Impact)

### 4. **Council Bots Run Sequentially** ⚠️ MEDIUM IMPACT
**Location:** `council/council.py` (all 14 bots run one after another)  
**Current:** Each bot waits for previous to finish before running  
**Why:** Bots are sorted by priority and executed in order, no parallelism  

**Fix:** Run independent bots in parallel (ThreadPoolExecutor)
- Bot dependencies: bot_01 → bot_06 → bot_08 (dag)
- Non-dependent bots can run parallel: bot_02, bot_03, bot_04, bot_05 (image healing, clipping, etc.)

**Estimated gain:** Council eval time drops from 30s → 10-15s (3 bots in parallel instead of serial)

---

### 5. **Orchestrator MAX_WORKERS = 4** ⚠️ MEDIUM IMPACT
**Location:** `orchestrator/empire_orchestrator.py` line 60  
**Current:** Only 4 concurrent mission workers  
**Scenario:** Josh running GG, LO, IL, ED in parallel = 4 threads consumed  
**Impact:** Any additional task (council eval, image scout, upload watcher) blocks

**Fix:** Increase to 8-12 workers, the orchestrator is just a task dispatcher
- Each worker is fast (mostly subprocess spawning)
- Real work happens in child processes (empire_render.py, council bots)

**Estimated gain:** No additional per-episode slowdown, but unlocks multi-project parallelism

---

### 6. **Image Fetch Delay = 1 second** ⚠️ MEDIUM IMPACT
**Location:** `empire_render.py` line 434, waterfall.py  
**Current:** `time.sleep(1.0)` between EACH image fetch to pace Pollinations  
**Why:** Pollinations rate-limits at ~1 req/sec  
**Problem:** Sleep applies to ALL providers (Wikimedia is instant, Pollinations is 1s, Gemini is 2-3s)

**Better approach:**
- Check which provider is handling THIS request
- Only sleep if it's Pollinations
- Wikimedia/WikiArt → no delay
- Gemini → handle 429 via exponential backoff, not blanket sleep

**Estimated gain:** Not massive, but 96 images × 0.5s saved per episode = 45s per episode

---

## ARCHITECTURAL BOTTLENECKS (High Impact, Complex Fix)

### 7. **70+ Scattered Render Scripts — Code Duplication** ⚠️ BLOCKING LONG-TERM
**Location:** repo root  
**Current:** 70+ Python files, many doing similar things:
- `empire_render.py`, `render_gg_v3.py`, `render.py`, `render_ml_ep001_win.py` (4 renders)
- `auto_render.py`, `empire_runner.py`, `pipeline_run.py` (3 runners)
- `channel_uploader.py`, `upload_gg_full.py`, `easy_youtube_uploader.py`, etc. (multiple uploaders)
- `book_pipeline.py`, `storyforge/`, `merch_empire/` (separate pipelines)

**Problem:** 
- No single source of truth for rendering
- Fixes to one aren't applied to others
- Maintenance nightmare
- Each has different parallelism/optimization levels

**Fix:** Consolidate to ONE render path that all projects use
- All 5 channels (GG, LO, IL, ED, EOE) through empire_render.py with --channel flag ✅ **Already done**
- Delete render_*.py, render_ml_*.py, old render.py

**Estimated gain:** 40% less code to maintain, easier to apply optimizations globally

---

### 8. **MISSION_BOARD.json File I/O Serialization** ⚠️ MEDIUM IMPACT
**Location:** `orchestrator/mission_board.py`, council system  
**Current:** Orchestrator + 14 council bots all read/write MISSION_BOARD.json  
**Contention:** At T=30, orchestrator reads board → executes render → bot_01 tries to write status update → bot_02 waits for lock  

**Fix options:**
- In-memory board during render (write once at end)
- Use a proper queue (Redis, RabbitMQ, or OS named pipes)
- SQLite with WAL mode for concurrent writes

**Estimated gain:** Eliminate 2-3s of lock contention per orchestrator cycle (might not be much)

---

### 9. **AI Router Not Caching Provider Selections** ⚠️ MEDIUM IMPACT
**Location:** `ai_router/router.py`  
**Current:** Every image request evaluates all 8 providers and their health scores  
**Overhead:** 200ms per decision × 96 images = 19 seconds per episode just on router overhead

**Fix:** Cache the best provider per task_type for 5 minutes
```python
def route(...):
    if cached_best_for_IMAGE_GENERATION and cache_age < 5min:
        return cached_best
    # else recalculate
```

**Estimated gain:** 15-20 seconds per episode (19s overhead → 2-3s initialization only)

---

## SUMMARY TABLE

| Bottleneck | Impact | Fix Effort | Estimated Gain |
|---|---|---|---|
| Scene parallelism (2→6) | 🔴 Critical | 1 line | 2-3x faster rendering |
| Poll interval (30→10s) | 🔴 Critical | 1 line | 25s latency per episode |
| Batch image fetches | 🔴 Critical | 20 lines | 3-4x faster images |
| Sequential council bots | 🟠 High | 30 lines | 2x council speed |
| Orchestrator MAX_WORKERS (4→12) | 🟠 High | 1 line | Multi-project unlocked |
| Smart image fetch delay | 🟡 Medium | 20 lines | 45s per episode |
| Consolidate render scripts | 🔴 Critical | 1-2 days | 40% code reduction, unified pipeline |
| Mission board queue | 🟡 Medium | 30 lines | 2-3s per cycle |
| Router provider caching | 🟡 Medium | 20 lines | 15-20s per episode |

---

## QUICK WINS (30 minutes to implement, 5-10 min gain each)

**Do these first:**
1. `MAX_PARALLEL_SCENES = 2` → `6` in empire_render.py
2. `POLL_INTERVAL_SEC = 30` → `10` in orchestrator
3. Remove blanket `sleep(1.0)` from image fetches, only sleep on Pollinations 429

These three alone buy Josh **2-3x faster overall throughput**.

---

## LONG-TERM RECOMMENDATIONS

1. **Delete 60 render/upload scripts** — route everything through empire_render.py + channel_uploader.py
2. **Event-based orchestrator** — watch MISSION_BOARD.json with inotify instead of polling every 30s
3. **Parallel council eval** — DAG-based bot execution (bot_01 → bot_06, bot_02||bot_03||bot_04 in parallel)
4. **Provider caching in AI Router** — avoid re-evaluating health scores every request
5. **Batch media operations** — one thread to fetch all 96 images for an episode instead of 24 sequential loops

---

## NEXT ACTION

**I recommend:**
1. Implement the 3 quick wins (5 minutes)
2. Test throughput improvement (5 minutes)
3. Then tackle long-term consolidation (1-2 days) once the quick wins prove the pattern

This will get you from **~15-20 min per GG episode** down to **~5-8 min** immediately, without touching the render quality or complexity.

Want me to build these fixes now?

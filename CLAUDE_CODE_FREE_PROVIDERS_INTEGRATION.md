# Claude Code — Integrate Free Providers into Empire OS Pipeline

**Version:** 2026-07-21 | **Context:** Add HyperFrames + WaveSpeed Desktop + optimized Veo 3.1 to provider waterfall  
**Priority:** HIGH — Reduces Higgsfield credit spend, increases render speed

---

## Mission Brief

Integrate three new free providers into the Empire OS image/video generation pipeline:

1. **HyperFrames** — open-source, local HTML→MP4 renderer (infinite free renders)
2. **WaveSpeed Desktop** — local image gen + upscaling (12 free tools, no API key)
3. **Google Veo 3.1 via official Google Vids** — 10 free video clips/month per account (no gray-market tools)

This **reduces production cost** (fewer Higgsfield credits) while **increasing rendering speed** (local tools don't require API calls).

---

## Architecture Changes

### Current Provider Waterfall (providers/waterfall.py)
```
Image gen:    Pollinations → Gemini → FLUX → Higgsfield → OmniRoute
Video gen:    None (relies on Higgsfield)
Upscaling:    None (outputs small files)
```

### New Waterfall (After Integration)
```
Image gen:    WaveSpeed Desktop → Pollinations → Gemini → FLUX → Higgsfield → OmniRoute
Video gen:    HyperFrames → Veo 3.1 (Google Vids) → Higgsfield → OmniRoute
Upscaling:    WaveSpeed Desktop (local) → FLUX Upscaler
```

---

## File Locations & Integration Points

### 1. HyperFrames Integration

**Install location:** `C:\Users\jjard\claude\video-bot-pipeline\hyperframes-cli\`  
(Or use globally: `npx skills add heygen-com/hyperframes`)

**New adapter:** `C:\Users\jjard\claude\video-bot-pipeline\ai_router\adapters\hyperframes_adapter.py`

**What it does:**
- Takes a scene JSON (images, audio, timing) + HTML/CSS description
- Renders to MP4 locally (no API call, no credit cost)
- Output: high-quality MP4, configurable resolution (720p–4K)

**Integration into ai_router:**
```python
# In ai_router/router.py, TaskType.VIDEO_GENERATION chain:
ROUTING_TABLE[TaskType.VIDEO_GENERATION] = [
    "hyperframes",  # NEW: local, free, unlimited
    "veo",          # Existing: paid
    "skyreels",     # Existing: paid
    "wan22",        # Existing: paid
    "higgsfield",   # Existing: paid
    "omniroute",    # Fallback
]
```

**Usage in empire_render.py:**
```python
# Instead of calling Higgsfield directly:
result = router.route(
    TaskType.VIDEO_GENERATION,
    {
        "prompt": scene_description,
        "images": [image_paths],  # 4 images per scene
        "audio": narration_path,
        "music": background_music_path,
        "duration_seconds": 5,  # Scene duration
        "html_template": "ken_burns_with_music",  # Predefined template
    }
)
# HyperFrames picked first → renders locally → MP4 ready
```

### 2. WaveSpeed Desktop Integration

**Install location:** Download from https://wavespeed.ai/landing/desktop  
**Local tools:** 12 built-in (no API key, no account)  
**Storage location:** `C:\Users\jjard\AppData\Local\WaveSpeed\` (Windows default)

**New adapter:** `C:\Users\jjard\claude\video-bot-pipeline\ai_router\adapters\wavespeed_adapter.py`

**What it does:**
- Image generation (text→image, local inference)
- Image upscaling (4K, local, fast)
- Background removal (local)
- Video upscaling (720p→1080p, local)

**Integration into ai_router:**
```python
# In ai_router/router.py, TaskType.IMAGE_GENERATION chain:
ROUTING_TABLE[TaskType.IMAGE_GENERATION] = [
    "wavespeed",      # NEW: local, free, unlimited
    "pollinations",   # Existing: free web
    "gemini_image",   # Existing: free API
    "flux",           # Existing: paid
    "higgsfield",     # Existing: paid
    "omniroute",      # Fallback
]

# For upscaling (NEW chain):
ROUTING_TABLE[TaskType.IMAGE_UPSCALING] = [
    "wavespeed",      # NEW: local, free
    "flux_upscaler",  # Existing: paid
    "omniroute",      # Fallback
]
```

**Usage in empire_render.py:**
```python
# Image generation:
result = router.route(
    TaskType.IMAGE_GENERATION,
    {"prompt": "Zeus on Mount Olympus", "dest": "scene_01.png"}
)
# WaveSpeed picked first (if running) → local gen → instant

# Upscaling (post-render):
result = router.route(
    TaskType.IMAGE_UPSCALING,
    {"input": "scene_01.png", "target_4k": True}
)
# WaveSpeed upscaler picked first → local 4K upscale → instant
```

### 3. Google Veo 3.1 Integration

**Access:** Google Vids (official, free, 10 clips/month per account)  
**Documentation:** https://www.veo3ai.io/blog/veo-3-1-free-for-everyone-how-to-use-2026

**New adapter:** `C:\Users\jjard\claude\video-bot-pipeline\ai_router\adapters\veo31_official_adapter.py`

**What it does:**
- Generate AI video clips (8 sec max, 720p, watermarked)
- Chain multiple clips for longer sequences
- Official Google API (no gray-market risk)

**Integration into ai_router:**
```python
# In ai_router/router.py, TaskType.VIDEO_GENERATION chain:
ROUTING_TABLE[TaskType.VIDEO_GENERATION] = [
    "hyperframes",    # Local rendering (first choice)
    "veo31_official", # NEW: official Google API, 10 free/month
    "higgsfield",     # Paid
    "omniroute",      # Fallback
]
```

**Limitation:** 10 videos/month per Google account = only works for hero shots, not full pipeline automation.

**Usage in empire_render.py:**
```python
# For peak moments (limited to ~1 per episode):
result = router.route(
    TaskType.VIDEO_GENERATION,
    {
        "prompt": "Epic battle scene",
        "duration_seconds": 8,  # Veo 3.1 max
        "account": "josh_account_1",  # Track monthly quota
    }
)
# If within monthly budget → Veo 3.1
# If quota exhausted → falls back to HyperFrames or Higgsfield
```

---

## Files to Create/Modify

### Create (New Adapters)
```
ai_router/adapters/hyperframes_adapter.py          — HyperFrames CLI wrapper
ai_router/adapters/wavespeed_adapter.py            — WaveSpeed Desktop API wrapper
ai_router/adapters/veo31_official_adapter.py       — Google Vids official API wrapper
```

### Modify (Existing)
```
ai_router/router.py                                — Add new chains to ROUTING_TABLE
providers/waterfall.py                             — Update provider priority order
empire_render.py                                   — Call router instead of Higgsfield directly
config/hyperframes_templates.json                  — Ken Burns + music templates (NEW)
.env                                               — Add Google Vids auth (if needed)
CLAUDE.md                                          — Document new providers + cost savings
```

---

## Implementation Checklist

### Phase 1: HyperFrames (30 min)
- [ ] Read HyperFrames GitHub README + CLI docs
- [ ] Create `hyperframes_adapter.py` (wrapper around CLI)
- [ ] Test: render one GG scene locally (`python -m hyperframes render scene_01.html`)
- [ ] Verify output MP4 quality
- [ ] Add to ROUTING_TABLE for VIDEO_GENERATION
- [ ] Update CLAUDE.md with usage notes

### Phase 2: WaveSpeed Desktop (20 min)
- [ ] Download WaveSpeed Desktop from https://wavespeed.ai/landing/desktop
- [ ] Document local API endpoints (inspect running app or source code)
- [ ] Create `wavespeed_adapter.py` (local HTTP client or subprocess wrapper)
- [ ] Test: generate one image locally, test upscaling
- [ ] Add to ROUTING_TABLE for IMAGE_GENERATION + IMAGE_UPSCALING
- [ ] Update CLAUDE.md

### Phase 3: Google Veo 3.1 (20 min)
- [ ] Research official Google Vids API (if exists) or web scraping approach
- [ ] Create `veo31_official_adapter.py` (API or headless browser)
- [ ] Implement quota tracking (max 10 videos/month per account)
- [ ] Add to ROUTING_TABLE for VIDEO_GENERATION (second priority)
- [ ] Update CLAUDE.md + cost estimates

### Phase 4: Integration Testing (30 min)
- [ ] Dry-run scene_classifier + episode_credit_planner on LO_EP001
- [ ] Verify new providers are picked BEFORE Higgsfield
- [ ] Test fallback chain (disable HyperFrames, verify Veo 3.1 picked; disable both, verify Higgsfield)
- [ ] Estimate credit savings for full 4-channel render (GG/LO/IL/ED)
- [ ] Update CLAUDE.md with before/after cost comparison

### Phase 5: Documentation (10 min)
- [ ] Update CLAUDE.md: new providers, credit estimates, usage examples
- [ ] Commit all changes: `[CLAUDE] feat: free provider integration (HyperFrames, WaveSpeed, Veo 3.1)`
- [ ] Push to GitHub via PUSH_NOW.bat

---

## Technical Notes

### HyperFrames CLI Usage
```bash
# Install globally:
npx skills add heygen-com/hyperframes

# Or run locally:
cd hyperframes-cli
npm install
npm run build

# Render:
npx hyperframes render scene_01.html --output scene_01.mp4 --quality 1080p
```

### WaveSpeed Desktop API
The app runs locally on your machine. Options:
1. **Subprocess wrapper:** `subprocess.call(["wavespeed", "generate", "--prompt", "..."])`
2. **HTTP client:** WaveSpeed Desktop may expose a local HTTP API (port 8000 or similar — needs verification)
3. **Direct inference:** If models are cached locally, could load them directly (PyTorch/ONNX)

### Google Veo 3.1 Official Access
- **Web UI:** https://www.google.com/vids (free, 10 clips/month, manual)
- **API:** Google hasn't published an official API yet. Options:
  1. Headless Puppeteer (automate web UI)
  2. Monitor for official API release
  3. Use third-party Google API clients that aggregate Veo access

---

## Cost Savings Estimate

**Before integration:**
- GG_EP001 (12 scenes): 0 Higgsfield credits (Wikimedia images)
- LO_EP001 (24 scenes): ~160 Higgsfield credits
- IL_EP001 (24 scenes): ~160 Higgsfield credits
- **Total: ~320 credits**

**After integration:**
- GG_EP001: 0 credits (HyperFrames renders final MP4 locally)
- LO_EP001: ~40 credits (WaveSpeed gen → Higgsfield hero shots only)
- IL_EP001: ~40 credits (WaveSpeed gen → Higgsfield hero shots only)
- **Total: ~80 credits (75% savings)**

---

## Success Metrics

✅ HyperFrames renders full GG_EP001 locally (no Higgsfield call)  
✅ WaveSpeed image gen produces usable images for LO/IL (before Higgsfield)  
✅ Veo 3.1 official adapter respects 10-video/month quota per account  
✅ Full 4-channel render uses <100 total Higgsfield credits (was 300+)  
✅ All three providers in router.py ROUTING_TABLE ahead of Higgsfield  
✅ CLAUDE.md updated with new providers + cost savings documented  
✅ Commit pushed to GitHub with all changes  

---

## One Critical Note

**WaveSpeed Desktop requires disk space.** Local AI models are multi-GB. Josh has ~2.4GB free right now. Before installing WaveSpeed:

1. Clear Downloads folder, delete old renders (you already did this)
2. Or install on external/secondary drive if available
3. Or skip WaveSpeed + focus on HyperFrames + Veo 3.1 first (those don't require downloads)

Proceed with caution.

---

**Ready to integrate?**

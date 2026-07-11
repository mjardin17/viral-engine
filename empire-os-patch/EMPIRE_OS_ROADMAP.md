# Empire OS — Architect's Roadmap
**Lead Architect:** Claude  
**Owner:** Josh Jardin  
**Mission:** The ultimate self-improving AI Operating System, running locally on Windows, requiring minimal manual work.

---

## What Empire OS Already Has (Foundation)

| Module | URL | Status |
|--------|-----|--------|
| Empire Assistant | `/empire-assistant/` | ✅ Live — Claude/Gemini/Ollama/OpenAI routing |
| Model Manager | `/model-manager/` | ✅ Live — install/remove/register Ollama models |
| AI Discovery | `/discovery/` | ✅ Live — curated catalog, HW compat, benchmarks |
| Health Monitor | `/health-monitor/` | ✅ Live — services, RAM/CPU/disk, event log |
| Media Engine | `/media-engine/` | ✅ Live — video/image/audio/music routing |
| Knowledge Base | `/knowledge-base/` | ✅ Live — persistent memory, searchable |

---

## Phase 1 — The Interface (THIS SESSION)
**Goal:** Make Empire OS feel like a premium desktop OS. One interface for everything.

| Deliverable | Description | Status |
|-------------|-------------|--------|
| **Empire Dashboard** | Glassmorphism SPA — unified UI for all modules, live stats, floating AI assistant | ✅ Done — opens at localhost:3001/ |
| **Empire Store** | One-click software catalog — AI models, video tools, audio, OCR, automation | ✅ Done — 40+ curated items |
| **Installer Service** | Downloads, verifies, configures, and registers everything automatically | ✅ Done — pip/npm/winget/ollama |

---

## Phase 2 — Intelligence (Next Session)
**Goal:** Empire OS actively discovers, benchmarks, and recommends improvements.

| Deliverable | Description |
|-------------|-------------|
| **Enhanced Discovery** | Real-time monitoring — GitHub trending, HuggingFace releases, Papers With Code, Reddit AI. Summarize with Ollama, score, alert |
| **Auto-Benchmark** | Run every installed model against 10 standardized tasks. Rank by speed/quality/cost. Update weekly |
| **Self-Improvement Engine** | Compares installed vs available — alerts on "Qwen 3 is 30% better than your current coder model" |
| **Electron Desktop Shell** | Wrap the web UI in Electron — native app, system tray, notifications |

---

## Phase 3 — Video Studio (Future)
**Goal:** End-to-end video production pipeline inside Empire OS.

| Deliverable | Description |
|-------------|-------------|
| **Video Studio UI** | ComfyUI + FFmpeg orchestrator — scene detection, B-roll, subtitles, thumbnail gen |
| **Shorts Factory** | Auto-generate YouTube Shorts, TikTok, Instagram from long-form video |
| **Voice Pipeline** | Whisper → script edit → Piper/Kokoro → lip-sync/video |
| **YouTube Packager** | Title, description, tags, thumbnail — all AI-generated, one-click upload |

---

## Phase 4 — Full Autonomy (Long-term)
**Goal:** Empire OS runs itself. Josh reviews and approves, but never has to do the work.

| Deliverable | Description |
|-------------|-------------|
| **Council Integration** | Empire OS supervises the 9 Council Bots — monitor, restart, upgrade |
| **Workflow Engine UI** | Drag-and-drop workflow builder — chain any Empire module |
| **Cross-App Memory** | One memory bus connecting StoryForge, CrossPost, Video Pipeline, Council Bots |
| **Scheduled Intelligence** | Daily briefing — what changed, what improved, what needs attention |

---

## AI Routing Architecture

```
Request Type         → Primary          → Fallback
──────────────────────────────────────────────────────
Simple chat          → Ollama           → Claude
Coding               → Ollama (Qwen)   → Claude
Architecture         → Claude           → Gemini
Research             → Gemini           → Claude
Scripts              → Gemini           → Ollama
Image gen            → ComfyUI/A1111   → DALL·E
Video gen            → ComfyUI/LTX     → Pika/Kling
Speech → Text        → Whisper.cpp     → Whisper-py
Text → Speech        → Piper           → Kokoro → ElevenLabs
Music                → MusicGen        → Suno
Computer control     → Goose           → Playwright
Offline mode         → Ollama only     → (no cloud)
```

---

## Hardware Optimization — Josh's 8GB Windows Laptop

```
RAM Budget:
  OS + Chrome + VS Code ≈ 3.0 GB
  Empire OS server      ≈ 0.2 GB
  Available for models  ≈ 4.8 GB

Best models for this machine:
  qwen2.5:7b      (4.7GB) ← primary text/code
  gemma3:4b       (3.0GB) ← fast, quality
  phi4-mini:3.8b  (2.6GB) ← reasoning
  llama3.2:3b     (2.0GB) ← small+fast
  llava:7b        (4.5GB) ← vision tasks
  moondream:1.8b  (1.1GB) ← instant vision

Do NOT install: anything >8B params at full precision
Safe to install: any 7B/8B model in 4-bit quantization
```

---

## Module Contract

Every module implements `EmpireModule` from `@empire-os/core`:
```typescript
interface EmpireModule {
  moduleId: string
  init(services: CoreServices, config: Record<string, unknown>): Promise<void>
  handleRequest(req: GatewayRequest): Promise<GatewayResponse>
  handleEvent(event: unknown): Promise<void>
  health(): Promise<ModuleHealth>
  shutdown(): Promise<void>
}
```

**Never break this contract.** All new modules extend, never replace.

---

## Empire Store — Software Catalog Structure

```
Categories:
  ai-models     → Ollama-pullable models
  video         → ComfyUI, FFmpeg, video generators
  image         → SD, FLUX, upscalers
  voice         → Whisper, Piper, Kokoro, cloners
  ocr           → PaddleOCR, Florence-2, SAM2
  automation    → Playwright, Goose extensions
  developer     → LM Studio, Open WebUI, tools
  research      → Paper readers, summarizers
  plugins       → Empire-native plugins

Install methods:
  ollama   → ollama pull <model>
  pip      → pip install <package>
  npm      → npm install -g <package>
  winget   → winget install <id>
  url      → open download page
  script   → run installer script
```

---

## Production Rules (Never Break)

1. **NEVER auto-install** — always ask Josh first
2. **NEVER commit .env** — API keys stay local
3. **NEVER delete renders/** — finished episodes are sacred
4. **No scene reuse** — ever, within or across episodes
5. **4 photos per scene** — non-negotiable
6. **Git format:** `[CLAUDE] feat/fix/docs/chore: description`
7. **Canonical folder:** `C:\Users\jjard\claude\video-bot-pipeline\`

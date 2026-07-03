# PROJECT_IDENTITY — CrossPost Enterprise (Empire OS)
**Empire Inspector Score:** 98% — KEEP
**Location:** https://ais-dev-7vc3anh5ikstpsjhmaywr7-767455093414.us-east1.run.app (Cloud Run)
**Stack:** Express v5, React 19 + Vite, Tailwind CSS v4, TypeScript
**Runtime:** Node.js (tsx for dev, node for prod)
**Port:** 3000

---

## What This Project Does
Empire OS v3.0 Enterprise — the central orchestration hub for Josh's entire AI ecosystem. Combines a multi-agent content publishing pipeline (CrossPost) with an AI routing layer, local Ollama center, project registry (Empire Inspector), analytics, automation/cron, and a documentary production console — all in a single web app. Branded as "Business Intelligence Workspace & Cognitive Routing Architecture."

## What Problems It Solves
- Routes every AI request to the optimal model (Ollama local / Gemini / Claude) automatically
- Takes raw creator input (scripts, transcripts, outlines) → multi-agent processing → platform-ready posts for YouTube, TikTok, Twitter, LinkedIn
- Registers and audits all Josh's projects in one CTO dashboard
- Tracks revenue ($4,850 MRR), CPM yields, audience growth projections
- Manages background cron jobs and task queues across the whole ecosystem
- Provides a settings hub for all credentials and model parameters

## What APIs It Exposes
**Content / Publishing:**
- `GET /api/platforms` — list all platform configs (YouTube, TikTok, Twitter, LinkedIn, Instagram)
- `POST /api/generate` — multi-agent content generation (Analyst → Director/Writer → Critic → scored output per platform)
- `POST /api/research-monetization` — niche research + CPM analysis

**Empire OS Core:**
- `GET /api/empire/register` — register an external project in the ecosystem
- `GET /api/empire/event-bus` — SSE stream: listen for cross-project events
- `POST /api/empire/event-bus` — publish an event to all listeners
- `POST /api/empire/ai-router` — route a task to Ollama/Gemini/Claude by type
- `POST /api/empire/goose-runtime` — GitHub Goose scraper (niche/competitive intel)

**Empire Inspector:**
- `GET /api/inspector/health` — ecosystem health report
- `POST /api/inspector/advisor` — get CTO recommendations for a project

**GitHub:**
- `GET /api/auth/github/url` — OAuth URL
- `GET /api/github/repos` — list synced repos
- `GET /api/github/audit-repo` — audit a repo's tech debt

**Ollama:**
- `GET /api/ollama/models` — list available local models
- `POST /api/ollama/models/register` — register a new model
- `GET /api/ollama/system-usage` — CPU/RAM/VRAM stats
- `POST /api/ollama/route` — dispatch a prompt to local LLM
- `GET /api/ollama/queue` — view execution queue
- `POST /api/ollama/queue/clear` — clear queue
- `POST /api/ollama/benchmark` — benchmark model latency

**Utilities:**
- `GET /api/download-for-claude` — export full codebase as structured text (requires browser session)
- `GET /api/export-codebase` — export codebase
- `GET /*` — serves React SPA (static files from dist/)

## What Files Are Important
| File | Role | Size |
|---|---|---|
| `server.ts` | Express backend, all API routes | ~90KB |
| `src/App.tsx` | Full React frontend (all sections) | ~136KB |
| `src/types.ts` | TypeScript interfaces: PlatformConfig, AnalystInsights, CriticReview, HookScoreBreakdown, PlatformGeneration, MultiAgentResponse | small |
| `src/components/MathEngine.tsx` | CPM scoring + arbitrage math | unknown |
| `src/components/SystemArchitecture.tsx` | System architecture visualization | unknown |
| `package.json` | Dependencies: @google/genai, express, react, recharts, lucide-react, motion, dotenv | small |

## What AI Models It Uses
| Model | Used For | Config |
|---|---|---|
| Gemini 2.0 Flash | Multi-agent content generation (primary) | `process.env.GEMINI_API_KEY` — SET |
| Ollama (local) | Local reasoning, code, SQL tasks | `http://localhost:11434` |
| Claude 3.5 Sonnet | Deep reasoning, multi-file architecture | Via AI Router routing rule |
| GitHub Goose | Competitive scraping / niche research | Simulated in current build |

**AI Router Routing Rules:**
- SQL / database structure → Ollama (llama3)
- Real-time search or grounding → Gemini 3.5 Flash
- Multi-file systems / deep reasoning → Claude 3.5 Sonnet

**Settings:**
- Model temperature entropy: 0.7
- Gateway mode: SIMULATED SANDBOX (not yet live)
- Temp file cache: 24 hours

## What Other Projects It Can Connect To
All 6 in the CTO Action Ledger + any project registered via `/api/empire/register`:
- **Video Bot Pipeline** — render triggers via Event Bus; completed finals via Content Ingress
- **StoryForge Engine** — script output feeds into Content Ingress
- **Documentary Factory** — voiceover/act structure feeds into Content Ingress
- **LTX Video Engine** — generated video frames via Event Bus
- **Auto Poster Bot** — receives publish jobs from Content Ingress
- **Boss Listers** — listing/copy output for platform descriptions

## What It Should NEVER Duplicate
- Video rendering (Video Bot Pipeline owns this — FFmpeg + auto_render.py)
- Long-form scripting (StoryForge Engine owns this)
- Frame interpolation / AI video generation (LTX Video Engine owns this)
- Lead validation / classified parsing (Boss Listers)
- Headless browser posting (Auto Poster Bot)

## Current Completion
**98%** per Empire Inspector
- Multi-agent pipeline: ✅ Complete
- AI Router: ✅ Complete
- Ollama Center: ✅ Complete
- Empire Inspector: ✅ Complete
- Analytics: ✅ Complete
- Automation/Cron: ✅ Complete
- Settings: ✅ Complete
- Content Ingress: ✅ Complete
- Monetization Center: ✅ Complete

## Missing Features
- Live platform API credentials (currently SIMULATED SANDBOX — no real YouTube/TikTok/Twitter posting)
- Real GitHub OAuth (currently simulated)
- Live Gemini API connection (toggle exists but in sandbox mode)
- Video Bot Pipeline not registered in Empire Inspector
- Webhook receivers for external project events (currently push-only Event Bus)

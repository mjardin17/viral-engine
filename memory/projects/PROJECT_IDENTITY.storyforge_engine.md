# PROJECT_IDENTITY — StoryForge Engine
**Empire Inspector Score:** 94% — KEEP
**Location:** Inside Empire OS (Creative Console → StoryForge)
**Stack:** FastAPI, Vue.js v3, Tailwind CSS, Python

---

## What This Project Does
Long-form narrative synthesis and scene sequencing pipeline. Takes a story premise, configures tone/audience/pacing parameters, and generates full script blueprints with scene cue structures and character matrices. Integrated into Empire OS's cognitive routing layer for AI-assisted script drafting.

## What Problems It Solves
- Generates structured multi-scene scripts from a single premise sentence
- Handles character matrix mapping across scenes
- Supports configurable tone profiles and pacing for different audiences
- Maintains a story archive for previously generated narratives

## What APIs It Exposes
Exposed via Empire OS (exact endpoints unknown — accessible through Empire OS AI Router):
- Story generation (premise → scene blueprint)
- Character matrix generation
- Story archive read/write

**Empire OS UI inputs:**
- Story working title (optional)
- Core premise / theme
- Target audience
- Tone profile
- Narrative pacing

**Outputs:**
- Full script blueprints
- Scene cue structures
- Character relationship matrices

## What Files Are Important
(Not locally accessible — lives in separate project)
- FastAPI backend (Python)
- Vue.js v3 frontend
- Story archive storage (format unknown — likely JSON or PostgreSQL)

## What AI Models It Uses
- Routed through Empire OS AI Router
- Long-form writing → Claude 3.5 Sonnet (per routing rules)
- Research/premise expansion → Gemini
- Local draft generation → Ollama

## What Other Projects It Can Connect To
- **Empire OS** — integrated into Creative Console
- **Documentary Factory** — StoryForge script → Documentary Factory for voiceover timing
- **Video Bot Pipeline** — StoryForge script (if formatted as episode JSON) → Video Bot Pipeline for rendering
- **Content Ingress** — finished scripts → multi-agent platform publishing

## What It Should NEVER Duplicate
- Video rendering (Video Bot Pipeline)
- Platform publishing (CrossPost / Content Ingress)
- Conversion copywriting (Boss Listers)
- Image generation (Video Bot Pipeline / Pollinations.ai)

## Current Completion
**94%** per Empire Inspector
- High completion, minor modernization tasks flagged (3 duplicate functions detected by Empire Inspector)

## Missing Features
- 3 duplicate functions need refactoring (flagged by Empire Inspector)
- Unknown: whether script output format matches Video Bot Pipeline's episode JSON schema
- Unknown: archive persistence (in-memory vs database)
- Direct export to Video Bot Pipeline episode JSON format (bridge to be built)

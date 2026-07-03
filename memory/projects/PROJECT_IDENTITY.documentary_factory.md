# PROJECT_IDENTITY — Documentary Factory
**Empire Inspector Score:** 72% — KEEP
**Location:** Inside Empire OS (Creative Console → Documentary Factory)
**Stack:** Flask, Celery, FFmpeg bindings, Python

---

## What This Project Does
Automated video generation and voiceover timing synchronizer. Generates professional documentary act structures, voiceover scripts, visual prompt directions, and sound queues. Configures audio accents, narration voice files, and synth tracks. Produces a Director Timeline of acts with visual prompt logs. Separate from the Video Bot Pipeline — focused on documentary structure and voiceover choreography rather than full pipeline rendering.

## What Problems It Solves
- Structures raw documentary concepts into timed acts with voiceover cues
- Generates visual prompt directions for each act
- Selects voice synthesizer and background synth per production
- Creates a director timeline: prompt logs for visual production

## What APIs It Exposes
Accessible inside Empire OS Creative Console:
- Documentary generation (title/theme → act structure + voiceover script + visual prompts)

**UI Inputs:**
- Documentary title / theme topic
- Narration cadence & tone (e.g. "Investigative & Dramatic (BBC-style)")
- Voice synthesizer (e.g. "British (BBC Dialect)")
- Background synth (e.g. "Retro Sub-bass Synth")

**Output:**
- Director Timeline with:
  - Act structure
  - Voiceover scripts per act
  - Visual prompt directions
  - Sound queue timing

## What Files Are Important
(Not locally accessible — lives in separate project)
- Flask server (Python)
- Celery task queue (async generation)
- FFmpeg bindings (audio/video timing sync)
- Director timeline storage (format unknown)

## What AI Models It Uses
- Routed through Empire OS AI Router
- Likely: Claude for long-form voiceover writing, Gemini for research/fact layers

## What Other Projects It Can Connect To
- **Empire OS** — integrated into Creative Console
- **StoryForge Engine** — StoryForge script → Documentary Factory for voiceover timing
- **Video Bot Pipeline** — Documentary Factory act structure + voiceover → Video Bot Pipeline renders the actual video
- **LTX Video Engine** — visual prompt directions from Documentary Factory → LTX for frame generation
- **Content Ingress** — finished documentary package → platform publishing

## What It Should NEVER Duplicate
- Actual video rendering (Video Bot Pipeline owns FFmpeg rendering pipeline)
- Platform publishing (CrossPost / Content Ingress)
- Conversion copywriting (Boss Listers)
- Full script writing (StoryForge Engine)

## Current Completion
**72%** per Empire Inspector
- Functional but incomplete
- 3 audit flags in Empire Inspector (modernization tasks)
- FFmpeg integration likely incomplete (hence 72%)

## Missing Features
- Full FFmpeg rendering pipeline (Video Bot Pipeline already has this — avoid duplication)
- Unknown: whether voiceover timing exports to Video Bot Pipeline's scene JSON format
- Director Timeline persistence (in-memory only?)
- Integration with Video Bot Pipeline or LTX Video Engine for actual frame generation
- Celery task queue may need broker configuration (Redis/RabbitMQ)

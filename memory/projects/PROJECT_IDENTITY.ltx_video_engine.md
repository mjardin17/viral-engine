# PROJECT_IDENTITY — LTX Video Engine
**Empire Inspector Score:** 88% — KEEP
**Location:** Separate project (not locally accessible)
**Stack:** Go (Golang), React 18, WebSockets

---

## What This Project Does
Cinematic frame interpolator and real-time canvas generator. Likely uses the LTX-Video open-source model (Lightricks) for AI video generation and frame interpolation. Real-time WebSocket interface suggests live canvas preview during generation.

## What Problems It Solves
- AI-native video frame generation (text/image → video frames)
- Cinematic motion interpolation between keyframes
- Real-time canvas rendering with WebSocket progress stream

## What APIs It Exposes
Unknown — not accessible in Empire OS UI directly. Likely:
- Frame generation endpoint (prompt → video frames)
- Real-time WebSocket stream for generation progress

## What Files Are Important
(Not locally accessible — separate Go project)
- Go backend server
- React 18 frontend (likely WebGL canvas)
- WebSocket handlers

## What AI Models It Uses
- LTX-Video (Lightricks open-source) — likely primary model
- Possibly other diffusion-based video models

## What Other Projects It Can Connect To
- **Video Bot Pipeline** — LTX Video Engine could replace/supplement Pollinations.ai for image/video generation
- **Documentary Factory** — visual prompt directions → LTX for frame generation
- **Empire OS** — registered in Empire Inspector

## What It Should NEVER Duplicate
- Publishing pipeline (CrossPost / Content Ingress)
- Narration/TTS (edge-tts or ElevenLabs in Video Bot Pipeline)
- Script writing (StoryForge)
- Listing optimization (Boss Listers)

## Current Completion
**88%** per Empire Inspector — near production ready

## Missing Features
- Unknown — high completion suggests mostly working
- Integration bridge to Video Bot Pipeline not built
- Integration bridge to Documentary Factory not built

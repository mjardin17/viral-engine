# FREE API SETUP — Provider Waterfall Keys

How to get every key the LO/IL provider waterfall can use.
Paste each key into `.env` (repo root). **Never commit `.env`.**

**Waterfall order (v2, 2026-07-16):**
Luma → **fal_video** → **hf_video (FREE, already connected)** → Pika → Minimax → Replicate → **image_to_video (FREE, already connected — real motion)** → Gemini image Ken Burns → Pollinations Ken Burns → Higgsfield (paid, last resort).

---

## ✅ CONNECTED RIGHT NOW (zero new signups)

### hf_video — real AI video via Hugging Face Inference Providers
- **Key:** `HF_TOKEN` — **already in `.env`**
- **What it does:** routes text-to-video to fal-ai through `router.huggingface.co`, billed against HF's monthly included free inference credits. Tries in quality order: **Wan2.2-T2V-A14B → HunyuanVideo → LTX-Video-13B-distilled** (live routes verified 2026-07-16; the provider re-checks live status at runtime).
- **Honest quota:** the free HF allowance is small — a few short clips/month. When exhausted the router returns 402 and the waterfall moves on automatically. **HF PRO ($9/mo) bumps this to $2/mo credits + better limits** if we ever want it — but that's not free, so it stays optional.
- Nothing to do.

### image_to_video — THE guaranteed-free motion fallback ⭐
- **Keys:** `GEMINI_API_KEY` + `HF_TOKEN` — **both already in `.env`**
- **What it does:** Gemini generates the still (free ~500/day; Pollinations backup, always free) → HF image-to-video animates it into a real 5-6s motion clip (**Wan2.2-I2V → LTX-2 → Wan2.1-I2V → LTXV-distilled → HunyuanVideo-I2V**).
- **Why it matters:** actual motion instead of a Ken Burns pan over a frozen frame — the single biggest free quality upgrade for LO/IL. Subject to the same small HF quota; when it runs out, the Ken Burns path below still guarantees a visual.
- Nothing to do.

### Gemini image — Ken Burns source
- ~500 images/day free (gemini-2.5-flash-image "Nano Banana"). `GEMINI_API_KEY` set and working. Nothing to do.

### Pollinations image — Ken Burns source
- Unlimited images, no signup, no key. Nothing to do.
- **Pollinations VIDEO (researched):** gen.pollinations.ai now serves video (Seedance, Veo alpha, Wan-Fast) but it costs **"Pollen" credits — not free**. If you ever fund Pollen, get an `sk_` key at gen.pollinations.ai and put it in `POLLINATIONS_API_KEY=`; we'll wire a provider then. Images remain free/keyless.

---

## 🎁 FREE-CREDIT SIGNUPS (one-time credits — worth claiming, ~10 min total)

### 1. fal.ai — BIGGEST free-credit win (provider already built: `fal_video`)
- **Free credits:** **~$10-20 one-time** on signup (reports vary; $20 with a business email). NO permanent free tier — prepaid credits only.
- **Claim:** https://fal.ai → sign up → https://fal.ai/dashboard/keys → create key → paste into `FAL_KEY=` in `.env`.
- **Default model:** `fal-ai/ltxv-13b-098-distilled` (cheapest real video — cents/clip, so $10 ≈ dozens-hundreds of clips). Set `FAL_VIDEO_MODEL=fal-ai/wan/v2.2-a14b/text-to-video` for max quality (burns credits faster). Avoid Kling 3 Pro on fal (~$0.22-0.28/sec).
- **Credit card:** not required for the signup credits.

### 2. Replicate — trial credits
- **Signup:** https://replicate.com (GitHub login, no card) → token at https://replicate.com/account/api-tokens → `REPLICATE_API_TOKEN=`.
- **Free:** small one-time trial credits; then pay-per-run (LTX ≈ $0.02-0.07/clip — cheapest paid video anywhere).

### 3. Minimax / Hailuo — trial credits
- **Signup:** https://platform.minimax.io → API Keys → `MINIMAX_API_KEY=`.
- **Free:** one-time trial credit ≈ 4-8 test videos. No ongoing free API tier. No card for trial.

### 4. Together.ai — trial credits
- **Signup:** https://api.together.xyz → key → (no dedicated provider needed).
- **Findings:** Together DOES host Wan2.2 T2V/I2V — and the **HF router can already reach Together with your existing HF_TOKEN**, so a separate Together account only adds their one-time signup credit (~$1, promos vary). Low priority.

### 5. Kling AI — web-only free tier ❌ for API
- **Web app:** 66 free credits/day ≈ 6×5s watermarked 720p videos — **web only, watermarked, not usable via API**.
- **API:** prepaid packs from $9.80 (100 units, 30-day validity). Not free — skip unless funded. `KLING_API_KEY=` slot already exists.

### 6. Luma Dream Machine — ❌ no free API
- ~80 free daily credits are **web-app only**; API is PAYG (~$0.32/gen) and needs a card. `LUMA_API_KEY=` stays empty until funded.

### 7. Pika Labs — ❌ no free API
- API requires Pro (~$28/mo). Free credits are web/Discord only. Skip.

### 8. Sora (OpenAI) — ❌ no free API
- Sora video API is paid per-second; free usage is the ChatGPT/Sora app only (watermarked, no API export). Skip.

### 9. Veo 3 (Google) — ⚠️ mostly paid
- Veo via Gemini API is paid-tier. AI Studio occasionally exposes limited free Veo *preview* quota — unreliable for pipeline use. `VEO_API_KEY` slot exists; not in the waterfall until quota is dependable.

### 10. Groq — ❌ no video
- Groq serves LLMs/whisper only. No video models. Confirmed skip.

---

## 🖥️ ComfyUI LOCAL inference — BLOCKED on hardware
- **Finding:** `PERFORMANCE_REPORT.md` records **no GPU detected** on this machine (Ollama runs CPU-only). Local T2V needs ≥8GB VRAM (LTX-Video minimum), 12GB+ for Wan 2.1/2.2. **CPU-only local video gen is not viable — do not attempt.**
- **If a GPU (RTX 3060 12GB or better) is ever added:**
  1. Install ComfyUI Windows portable: https://github.com/comfyanonymous/ComfyUI/releases
  2. Best quality: **Wan 2.2 5B (TI2V)** — fits 8-12GB with GGUF quants; workflow templates ship in ComfyUI (Workflow → Browse Templates → Video).
  3. Fastest: **LTX-Video / LTX-2 distilled** — 768p clips in under a minute on a 3060.
  4. Then we wire a `providers/comfy_local.py` hitting `http://localhost:8188` — unlimited free local video, top of the waterfall.
- Until then: cloud-free routes above are the play.

---

## Quick test after adding a key
```
cd C:\Users\jjard\claude\video-bot-pipeline
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -c "from providers.waterfall import _video_chain; [print(n, f().is_connected()) for n, f in _video_chain()]"
```
`True` = key detected, provider will be tried. Expected right now:
`hf_video True`, `image_to_video True`, `replicate True` (HF fallback), rest `False` until keys are added.

## One-scene smoke test (uses a few cents of HF free credits)
```
cd C:\Users\jjard\claude\video-bot-pipeline
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -c "from pathlib import Path; from providers.waterfall import generate_scene_asset; a = generate_scene_asset('Little Zeus, a cheerful cartoon toddler god, waves from a cloud above Mount Olympus, bright storybook style', 6, '16:9', Path('output/waterfall_test'), 'smoke'); print(a)"
```

## Rendering without pre-made clips
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe empire_render.py --channel LO --episode LO_EP002
```
No `--clips-dir` → the waterfall auto-generates every scene clip.

# FREE API SETUP — Provider Waterfall Keys

How to get every key the LO/IL provider waterfall can use.
Paste each key into `.env` (repo root). Never commit `.env`.

Waterfall order: Luma → Pika → Minimax → Replicate → **Gemini image (free, already working)** → **Pollinations image (free, no key)** → Higgsfield (paid, last resort).

**Honest research note (July 2026):** none of the big video generators offer a truly free *API* tier anymore — free tiers are web-app only. The guaranteed always-free path is Gemini image + Pollinations image → Ken Burns, which needs nothing new. The video keys below light up better motion when/if you fund them.

---

## 1. Gemini image — ALREADY DONE ✅
- **Free tier:** ~500 images/day (gemini-2.5-flash-image "Nano Banana"), no credit card
- **Key:** `GEMINI_API_KEY` — already in `.env` and confirmed working
- Nothing to do.

## 2. Pollinations — ALREADY DONE ✅
- **Free tier:** unlimited images, no signup, no key, no credit card
- Nothing to do. (Their new video endpoints at gen.pollinations.ai cost "Pollen" credits — images stay free.)

## 3. Replicate — best cheap video option
- **Signup:** https://replicate.com (GitHub login, no credit card to start)
- **Copy:** API token from https://replicate.com/account/api-tokens
- **Paste into:** `REPLICATE_API_TOKEN=`
- **Free tier:** small trial credits on new accounts + limited free runs on featured models; then pay-per-run (LTX-Video ≈ $0.02–0.07 per short clip — cheapest real video)
- **Credit card:** not required for trial; required to keep going
- Also: the waterfall's Replicate provider falls back to your existing `HF_TOKEN` (Hugging Face Inference free monthly credits) automatically — that part needs no signup.

## 4. Minimax / Hailuo
- **Signup:** https://platform.minimax.io → Account → API Keys
- **Copy:** API key (long JWT string)
- **Paste into:** `MINIMAX_API_KEY=`
- **Free tier:** small trial credit on new accounts (roughly 4–8 test videos); after that pay-as-you-go (~1 point per 768p/6s clip). No ongoing free API tier.
- **Credit card:** not required for the trial

## 5. Luma AI Dream Machine
- **Signup:** https://lumalabs.ai/api → create account → API Keys
- **Copy:** key from the Dream Machine API dashboard
- **Paste into:** `LUMA_API_KEY=`
- **Free tier:** NONE for the API (~$0.32/generation PAYG). The ~80 free daily credits are web-app only and do NOT transfer to the API.
- **Credit card:** required for API use

## 6. Pika Labs
- **Signup:** https://pika.art → Settings → Developer → API Keys
- **Copy:** API key (requires **Pro** plan, ~$28/mo)
- **Paste into:** `PIKA_API_KEY=`
- **Free tier:** NONE for the API ($0.05/generated second). Free 80 credits/mo are web/Discord only.
- **Credit card:** required
- Skip this one unless you already pay for Pika.

## 7. Higgsfield (paid — already in the stack)
- `HIGGSFIELD_API_KEY=` in `.env`. Only used when everything above fails.

---

## Quick test after adding a key
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -c "from providers.waterfall import _video_chain; [print(n, f().is_connected()) for n, f in _video_chain()]"
```
Run from the repo root. `True` = key detected, provider will be tried.

## Rendering without pre-made clips
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe empire_render.py --channel LO --episode LO_EP002
```
No `--clips-dir` → the waterfall auto-generates every scene clip.

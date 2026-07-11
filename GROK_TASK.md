# GROK BUILD TASK — Empire OS API Upgrade
# Run this in the repo root: C:\Users\jjard\claude\video-bot-pipeline\
# Requires: SuperGrok or X Premium+
# Install: irm https://x.ai/cli/install.ps1 | iex

## Context

This is Empire OS — a multi-channel AI YouTube content pipeline.
Owner: Josh Jardin. CTO authority is held by the AI agent.
Read CLAUDE.md fully before touching anything. It is the source of truth.

## Your Job

Upgrade two Python files from the OLD Gemini SDK to the NEW Interactions API.
Do NOT touch any other files unless required for the upgrade.
Do NOT change logic, routes, services, or pipeline behavior — API swap only.

---

## UPGRADE 1 — empire_ads.py

**File:** `empire_ads.py` (root of repo)

### OLD (remove this):
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
data = json.loads(response.text)
```

### NEW (replace with this):
```python
from google import genai as google_genai
from google.genai import types

_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# In generate_service_ad():
interaction = _client.interactions.create(
    model="gemini-3.5-flash",
    input=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
    ),
)
data = json.loads(interaction.output_text)
```

### Rules:
- Model: `gemini-3.5-flash` (NOT gemini-1.5-flash)
- Client is module-level singleton `_client`
- Keep the fallback dict in the except block — just update the exception handler to catch the new SDK errors
- Keep all SERVICES, PLATFORMS, POST_TIMES, CLI args — untouched
- Keep save_schedule(), generate_weekly_schedule() — untouched except the generate_service_ad() call inside generate_weekly_schedule() already calls generate_service_ad() which you're fixing

---

## UPGRADE 2 — gemini-empire-agent/main.py

**File:** `gemini-empire-agent/main.py`

### OLD (remove this):
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
gemini_response = model.generate_content(task)
return {"result": result.get("messages", ["Success"]), "gemini": gemini_response.text[:200]}
```

### NEW (replace with this):
```python
from google import genai as google_genai

_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# In run_task(), replace the gemini fallback block:
interaction = _client.interactions.create(
    model="gemini-3.5-flash",
    input=task,
)
return {
    "result": result.get("result") or result.get("messages", ["Done"]),
    "gemini_summary": interaction.output_text[:300],
    "status": "ok",
}
```

### Rules:
- Module-level `_client` singleton
- FastAPI app stays on port 8000, uvicorn workers=4 — do not change
- `/run` endpoint signature stays: `async def run_task(task: str)`
- graph.invoke() call stays — the Gemini call is ONLY a summary fallback after the graph runs
- Keep SelfHealingSystem and healing.report_error() in the except block

---

## UPGRADE 3 — requirements / deps

Check if `gemini-empire-agent/requirements.txt` exists.
If yes: replace `google-generativeai` line with `google-genai>=2.9.0`
If no requirements.txt exists: create one with:
```
google-genai>=2.9.0
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
langgraph>=0.1.0
python-dotenv>=1.0.0
```

Also check root `requirements.txt` — same swap: `google-generativeai` → `google-genai>=2.9.0`

---

## UPGRADE 4 — research_agent.py (if it exists)

**File:** `research_agent.py` (check root and gemini-empire-agent/)

If found, upgrade to Deep Research:
```python
from google import genai as google_genai

_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def run_deep_research(topic: str) -> str:
    """Run Deep Research Max on a topic. Returns full report text."""
    import time
    
    interaction = _client.interactions.create(
        input=topic,
        agent="deep-research-max-preview-04-2026",
        background=True,
        agent_config={
            "type": "deep-research",
            "visualization": "auto",
        },
    )
    
    # Poll until complete
    while True:
        result = _client.interactions.get(interaction.id)
        if result.status == "completed":
            break
        elif result.status == "failed":
            raise RuntimeError(f"Deep Research failed: {result.error}")
        time.sleep(10)
    
    # Extract text from steps
    for step in result.steps:
        if step.type == "model_output" and step.content:
            for content in step.content:
                if content.type == "text":
                    return content.text
    return ""
```

If research_agent.py does NOT exist, skip this step.

---

## After All Changes

Run this verification:
```bash
cd C:\Users\jjard\claude\video-bot-pipeline
python -c "from google import genai; print('SDK OK')"
python -c "import empire_ads; print('empire_ads imports OK')"
```

Then commit:
```bash
git add -A
git commit -m "[GROK] feat: upgrade to google-genai>=2.9.0 + gemini-3.5-flash + Interactions API"
git push origin main
```

---

## What NOT to Touch

- auto_render.py — do not touch (separate upgrade, Josh will handle)
- council/ — do not touch
- prompts/ — do not touch
- renders/ — do not touch
- .env — NEVER touch, never read API keys aloud
- CLAUDE.md — do not touch
- agent_graph.py — do not touch (already upgraded)
- Any .mp4, .wav, .mp3 files — never commit these

---

## Done

Report back:
1. Which files were changed
2. Whether verification passed
3. Any import errors or missing deps
4. The git commit hash

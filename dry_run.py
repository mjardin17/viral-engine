"""
dry_run.py — Empire OS full-pipeline preflight (NO expensive generation).

    python dry_run.py

Runs 7 check groups and writes DRY_RUN_REPORT.md (✅ / ⚠️ / ❌ per check):
  1. Python dependencies      — import every adapter
  2. API connectivity         — ping provider endpoints (free/cheap only)
  3. Authentication           — validate keys with free account/list calls
  4. File paths               — prompts/, renders/, music/, assets/ etc.
  5. Storage space            — warn under 20GB, fail under 5GB
  6. Pipeline logic           — script resolution + ffmpeg/ffprobe + TTS wiring
  7. Council health           — all bots + all roles load and instantiate

Never generates images/video/audio. Never spends credits.
"""

from __future__ import annotations

import importlib
import json
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

REPORT_PATH = BASE_DIR / "DRY_RUN_REPORT.md"

OK, WARN, FAIL = "✅", "⚠️", "❌"


@dataclass
class Check:
    section: str
    name: str
    status: str   # OK / WARN / FAIL icon
    detail: str = ""


CHECKS: list[Check] = []


def add(section: str, name: str, status: str, detail: str = "") -> None:
    CHECKS.append(Check(section, name, status, detail))
    print(f"  {status} [{section}] {name}" + (f" — {detail}" if detail else ""))


# ── 1. Python dependencies ─────────────────────────────────────────────────────
ADAPTER_MODULES = [
    "ai_router.adapters.claude_adapter", "ai_router.adapters.openai_adapter",
    "ai_router.adapters.gemini_adapter", "ai_router.adapters.flux_adapter",
    "ai_router.adapters.flux_kontext_adapter", "ai_router.adapters.musetalk_adapter",
    "ai_router.adapters.skyreels_adapter", "ai_router.adapters.wan22_adapter",
    "ai_router.adapters.higgsfield_adapter", "ai_router.adapters.elevenlabs_adapter",
    "ai_router.adapters.kokoro_adapter", "ai_router.adapters.piper_adapter",
    "ai_router.adapters.whisper_adapter", "ai_router.adapters.ffmpeg_adapter",
    "ai_router.adapters.freepd_adapter", "ai_router.adapters.openverse_adapter",
    "ai_router.adapters.picsum_adapter", "ai_router.adapters.pollinations_adapter",
    "ai_router.adapters.ai_horde_adapter", "ai_router.adapters.uploader_adapter",
]


def check_dependencies() -> None:
    print("\n[1/7] Python dependencies")
    for mod in ADAPTER_MODULES:
        try:
            importlib.import_module(mod)
            add("deps", mod.rsplit(".", 1)[-1], OK)
        except ImportError as e:
            add("deps", mod.rsplit(".", 1)[-1], FAIL, f"ImportError: {e}")
        except Exception as e:
            add("deps", mod.rsplit(".", 1)[-1], FAIL, str(e))
    for optional, why, pkg in (
            ("whisper", "SUBTITLE_CREATION", "openai-whisper"),
            ("gradio_client", "skyreels/musetalk Space fallback", "gradio_client")):
        try:
            importlib.import_module(optional)
            add("deps", f"optional: {optional}", OK)
        except ImportError:
            add("deps", f"optional: {optional}", WARN,
                f"not installed — {why} unavailable (pip install {pkg})")


# ── 2. API connectivity ────────────────────────────────────────────────────────
ENDPOINTS = [
    ("pollinations", "https://image.pollinations.ai/", None),
    ("wikimedia", "https://commons.wikimedia.org/w/api.php", None),
    ("fal", "https://queue.fal.run/", "FAL_KEY"),
    ("replicate", "https://api.replicate.com/", "REPLICATE_API_TOKEN"),
    ("huggingface", "https://huggingface.co/api/whoami-v2", "HF_TOKEN"),
    ("openai", "https://api.openai.com/", "OPENAI_API_KEY"),
    ("elevenlabs", "https://api.elevenlabs.io/", "ELEVENLABS_API_KEY"),
    ("gemini", "https://generativelanguage.googleapis.com/", "GEMINI_API_KEY"),
]


def _ping(url: str, timeout: int = 10) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # 4xx means the host is up (auth checked separately)
        return e.code < 500, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def check_connectivity() -> None:
    print("\n[2/7] API connectivity")
    from ai_router.adapters.base_adapter import env
    for name, url, key in ENDPOINTS:
        if key and not env(key):
            add("connectivity", name, WARN, f"{key} not set — skipped")
            continue
        up, detail = _ping(url)
        add("connectivity", name, OK if up else FAIL, detail)


# ── 3. Authentication (free/cheap validation calls) ────────────────────────────
def _auth_get(url: str, headers: dict) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0",
                                               **headers})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} — key invalid/expired?"
    except Exception as e:
        return False, str(e)


def check_auth() -> None:
    print("\n[3/7] Authentication")
    from ai_router.adapters.base_adapter import env
    checks = [
        ("OPENAI_API_KEY", "https://api.openai.com/v1/models",
         lambda k: {"Authorization": f"Bearer {k}"}),
        ("ELEVENLABS_API_KEY", "https://api.elevenlabs.io/v1/user",
         lambda k: {"xi-api-key": k}),
        ("HF_TOKEN", "https://huggingface.co/api/whoami-v2",
         lambda k: {"Authorization": f"Bearer {k}"}),
        ("REPLICATE_API_TOKEN", "https://api.replicate.com/v1/account",
         lambda k: {"Authorization": f"Bearer {k}"}),
        ("GEMINI_API_KEY",
         "https://generativelanguage.googleapis.com/v1beta/models",
         lambda k: {"x-goog-api-key": k}),
    ]
    for key_name, url, header_fn in checks:
        key = env(key_name)
        if not key:
            add("auth", key_name, WARN, "not set")
            continue
        ok, detail = _auth_get(url, header_fn(key))
        add("auth", key_name, OK if ok else FAIL, detail)
    for key_name in ("FAL_KEY", "HIGGSFIELD_API_KEY", "ANTHROPIC_API_KEY"):
        add("auth", key_name, OK if env(key_name) else WARN,
            "set (no free validation endpoint — validated on first use)"
            if env(key_name) else "not set")


# ── 4. File paths ──────────────────────────────────────────────────────────────
EXPECTED_DIRS = ["prompts", "prompts/gods_glory", "renders", "music",
                 "output", "council/bots", "council/roles", "providers",
                 "voice-music-factory", "social_clips"]


def check_paths() -> None:
    print("\n[4/7] File paths")
    for rel in EXPECTED_DIRS:
        p = BASE_DIR / rel
        add("paths", rel, OK if p.exists() else WARN,
            "" if p.exists() else "missing")
    for rel in ("empire_render.py", "channel_uploader.py",
                "voice-music-factory/tts_cli.py", "video_effects.py"):
        p = BASE_DIR / rel
        add("paths", rel, OK if p.exists() else FAIL,
            "" if p.exists() else "MISSING — pipeline broken")


# ── 5. Storage ─────────────────────────────────────────────────────────────────
def check_storage() -> None:
    print("\n[5/7] Storage space")
    try:
        free_gb = shutil.disk_usage(str(BASE_DIR)).free / 1024**3
        if free_gb < 5:
            add("storage", "free space", FAIL, f"{free_gb:.1f}GB — renders WILL fail")
        elif free_gb < 20:
            add("storage", "free space", WARN, f"{free_gb:.1f}GB — cleanup soon")
        else:
            add("storage", "free space", OK, f"{free_gb:.0f}GB free")
    except Exception as e:
        add("storage", "free space", FAIL, str(e))


# ── 6. Pipeline logic (no generation) ──────────────────────────────────────────
def check_pipeline_logic() -> None:
    print("\n[6/7] Pipeline logic")
    try:
        from empire_render import FFMPEG, FFPROBE, find_episode_script
        add("pipeline", "ffmpeg", OK, FFMPEG)
        add("pipeline", "ffprobe", OK, FFPROBE)
        script = find_episode_script("GG", "GG_EP001")
        if script:
            data = json.loads(script.read_text(encoding="utf-8"))
            scenes = len(data.get("scenes", []))
            add("pipeline", "script resolution (GG_EP001)", OK,
                f"{script.name} — {scenes} scenes")
        else:
            add("pipeline", "script resolution (GG_EP001)", WARN,
                "no GG_EP001 script found in prompts/gods_glory/")
    except Exception as e:
        add("pipeline", "empire_render import", FAIL, str(e))
    try:
        from ai_router.router import AIRouter, TaskType
        router = AIRouter()
        for task in TaskType.all():
            best = router.get_best_model(task)
            connected = bool(best) and router._get_adapter(best) is not None \
                and router._safe_connected(router._get_adapter(best))
            add("pipeline", f"route {task}", OK if connected else WARN,
                f"→ {best}" + ("" if connected else " (not connected)"))
    except Exception as e:
        add("pipeline", "ai_router", FAIL, str(e))
    try:
        from pipeline_validator import PipelineValidator
        v = PipelineValidator().validate_prompt(
            "Leonidas at Thermopylae, historical oil painting, cinematic lighting")
        add("pipeline", "validator", OK if v.passed else FAIL,
            f"prompt score {v.score}")
    except Exception as e:
        add("pipeline", "validator", FAIL, str(e))


# ── 7. Council health ──────────────────────────────────────────────────────────
def check_council() -> None:
    print("\n[7/7] Council health")
    try:
        from council.council import discover_bots
        bots = discover_bots()
        add("council", "bot discovery", OK if bots else FAIL,
            f"{len(bots)} bot(s) load cleanly")
        for cls in bots:
            try:
                cls(base_dir=BASE_DIR, verbose=False, channel="gg")
                add("council", cls.name, OK)
            except Exception as e:
                add("council", cls.name, FAIL, f"instantiation failed: {e}")
    except Exception as e:
        add("council", "bot discovery", FAIL, str(e))
    try:
        from council.roles.run_roles import ALL_ROLES
        for cls in ALL_ROLES:
            try:
                cls(channel="gg")
                add("council", cls.name, OK)
            except Exception as e:
                add("council", cls.name, FAIL, str(e))
    except Exception as e:
        add("council", "roles", FAIL, str(e))


# ── report ─────────────────────────────────────────────────────────────────────
def write_report() -> Path:
    counts = {OK: 0, WARN: 0, FAIL: 0}
    for c in CHECKS:
        counts[c.status] = counts.get(c.status, 0) + 1
    lines = [
        "# Empire OS Dry Run Report",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Result:** {counts[OK]} ✅ / {counts[WARN]} ⚠️ / {counts[FAIL]} ❌",
        "",
    ]
    section = ""
    for c in CHECKS:
        if c.section != section:
            section = c.section
            lines += [f"## {section}", ""]
        lines.append(f"- {c.status} **{c.name}**"
                     + (f" — {c.detail}" if c.detail else ""))
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


def run_dry_run() -> int:
    """Run all checks; returns number of hard failures."""
    print("=" * 60)
    print("  EMPIRE OS DRY RUN — no assets generated, no credits spent")
    print("=" * 60)
    check_dependencies()
    check_connectivity()
    check_auth()
    check_paths()
    check_storage()
    check_pipeline_logic()
    check_council()
    path = write_report()
    fails = sum(1 for c in CHECKS if c.status == FAIL)
    warns = sum(1 for c in CHECKS if c.status == WARN)
    print(f"\n{'=' * 60}")
    print(f"  DRY RUN COMPLETE — {fails} failure(s), {warns} warning(s)")
    print(f"  Report: {path}")
    print("=" * 60)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run_dry_run() else 0)

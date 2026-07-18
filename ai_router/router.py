"""
Empire OS — Central AI Router
Routes every task to the best available model based on:
quality, speed, cost, availability, retry history, user preferences.

ADDITIVE layer: existing pipeline paths (providers/waterfall.py, direct
provider calls in empire_render.py) keep working untouched. New code should
route through AIRouter; old code migrates gradually.

Usage:
    from ai_router.router import AIRouter, TaskType
    router = AIRouter()
    result = router.route(TaskType.IMAGE_GENERATION, {"prompt": "...", "dest": "out.png"})
"""

from __future__ import annotations

import importlib
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_DIR: Path = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ai_router.adapters.base_adapter import AdapterBase, AdapterResult  # noqa: E402
from ai_router.model_health import ModelHealth  # noqa: E402

TAG = "[ai_router]"


class TaskType:
    """Canonical task type constants — use these exact strings everywhere."""

    PLANNING = "PLANNING"
    WRITING = "WRITING"
    STORYBOARDING = "STORYBOARDING"
    PROMPT_CREATION = "PROMPT_CREATION"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    IMAGE_EDITING = "IMAGE_EDITING"
    ANIMATION = "ANIMATION"
    VIDEO_GENERATION = "VIDEO_GENERATION"
    LIP_SYNC = "LIP_SYNC"
    NARRATION = "NARRATION"
    SUBTITLE_CREATION = "SUBTITLE_CREATION"
    MUSIC = "MUSIC"
    RENDERING = "RENDERING"
    PUBLISHING = "PUBLISHING"

    @classmethod
    def all(cls) -> list[str]:
        return [v for k, v in vars(cls).items()
                if k.isupper() and isinstance(v, str)]


# Default best-first routing per task type
ROUTING_TABLE: dict[str, list[str]] = {
    TaskType.PLANNING: ["claude", "chatgpt", "gemini"],
    TaskType.WRITING: ["claude", "chatgpt", "gemini"],
    TaskType.STORYBOARDING: ["claude", "gemini", "chatgpt"],
    TaskType.PROMPT_CREATION: ["claude", "chatgpt", "gemini"],
    TaskType.IMAGE_GENERATION: ["flux", "gemini_image", "pollinations", "ai_horde", "picsum"],
    TaskType.IMAGE_EDITING: ["flux_kontext", "chatgpt_vision", "gemini_vision"],
    TaskType.ANIMATION: ["wan22", "higgsfield", "kling", "skyreels"],
    TaskType.VIDEO_GENERATION: ["veo", "skyreels", "wan22", "runway", "higgsfield"],
    TaskType.LIP_SYNC: ["musetalk", "sadtalker"],
    TaskType.NARRATION: ["kokoro", "elevenlabs", "piper"],
    TaskType.SUBTITLE_CREATION: ["whisper"],
    TaskType.MUSIC: ["freepd", "openverse_audio"],
    TaskType.RENDERING: ["ffmpeg"],
    TaskType.PUBLISHING: ["channel_uploader"],
}

# model name → (module, class). Lazy imports so one broken adapter never
# kills the router. Models with no adapter yet (sadtalker/veo/runway) are
# skipped as unavailable — the fallback chain moves past them.
ADAPTER_REGISTRY: dict[str, tuple[str, str]] = {
    "claude": ("ai_router.adapters.claude_adapter", "ClaudeAdapter"),
    "chatgpt": ("ai_router.adapters.openai_adapter", "OpenAIAdapter"),
    "chatgpt_vision": ("ai_router.adapters.openai_adapter", "OpenAIAdapter"),
    "gemini": ("ai_router.adapters.gemini_adapter", "GeminiAdapter"),
    "gemini_image": ("ai_router.adapters.gemini_adapter", "GeminiAdapter"),
    "gemini_vision": ("ai_router.adapters.gemini_adapter", "GeminiAdapter"),
    "flux": ("ai_router.adapters.flux_adapter", "FluxAdapter"),
    "flux_kontext": ("ai_router.adapters.flux_kontext_adapter", "FluxKontextAdapter"),
    "pollinations": ("ai_router.adapters.pollinations_adapter", "PollinationsAdapter"),
    "ai_horde": ("ai_router.adapters.ai_horde_adapter", "AIHordeAdapter"),
    "picsum": ("ai_router.adapters.picsum_adapter", "PicsumAdapter"),
    "wan22": ("ai_router.adapters.wan22_adapter", "Wan22Adapter"),
    "skyreels": ("ai_router.adapters.skyreels_adapter", "SkyReelsAdapter"),
    "higgsfield": ("ai_router.adapters.higgsfield_adapter", "HiggsfieldAdapter"),
    "musetalk": ("ai_router.adapters.musetalk_adapter", "MuseTalkAdapter"),
    "kokoro": ("ai_router.adapters.kokoro_adapter", "KokoroAdapter"),
    "elevenlabs": ("ai_router.adapters.elevenlabs_adapter", "ElevenLabsAdapter"),
    "piper": ("ai_router.adapters.piper_adapter", "PiperAdapter"),
    "whisper": ("ai_router.adapters.whisper_adapter", "WhisperAdapter"),
    "ffmpeg": ("ai_router.adapters.ffmpeg_adapter", "FFmpegAdapter"),
    "freepd": ("ai_router.adapters.freepd_adapter", "FreePDAdapter"),
    "openverse_audio": ("ai_router.adapters.openverse_adapter", "OpenverseAdapter"),
    "channel_uploader": ("ai_router.adapters.uploader_adapter", "UploaderAdapter"),
}


@dataclass
class RouterResult:
    """Outcome of one routed task, including everything tried on the way."""

    model_used: str
    result: Any
    fallbacks_tried: list[str] = field(default_factory=list)
    latency_ms: int = 0
    cost_usd: float = 0.0
    success: bool = False
    error: str | None = None


class AIRouter:
    """Central router: task in → best available model executes → result out."""

    def __init__(self, health: ModelHealth | None = None) -> None:
        self.health = health or ModelHealth()
        self._adapter_cache: dict[str, AdapterBase | None] = {}

    # ── adapter loading ───────────────────────────────────────────────────
    def _get_adapter(self, model: str) -> AdapterBase | None:
        """Instantiate (and cache) the adapter for a model. None if missing."""
        if model in self._adapter_cache:
            return self._adapter_cache[model]
        entry = ADAPTER_REGISTRY.get(model)
        adapter: AdapterBase | None = None
        if entry is not None:
            module_name, class_name = entry
            try:
                mod = importlib.import_module(module_name)
                adapter = getattr(mod, class_name)()
            except Exception as e:
                print(f"{TAG} adapter load failed for {model}: {e}", file=sys.stderr)
        self._adapter_cache[model] = adapter
        return adapter

    # ── chain building ────────────────────────────────────────────────────
    def _chain_for(self, task_type: str, preferences: dict | None = None) -> list[str]:
        """Model order for a task: preferences → health-informed → defaults."""
        defaults = list(ROUTING_TABLE.get(task_type, []))
        prefs = (preferences or {}).get("models") or []
        chain = [m for m in prefs if m in defaults or m in ADAPTER_REGISTRY]
        # Health-sorted models that have real history for this task go next
        for m in self.health.recommend_routing(task_type):
            if m in defaults and m not in chain:
                chain.append(m)
        for m in defaults:
            if m not in chain:
                chain.append(m)
        return chain

    def get_best_model(self, task_type: str) -> str:
        """Best CONNECTED model for a task (health scores break ties)."""
        for model in self._chain_for(task_type):
            adapter = self._get_adapter(model)
            if adapter is not None and self._safe_connected(adapter):
                return model
        chain = ROUTING_TABLE.get(task_type, [])
        return chain[0] if chain else ""

    def get_fallback_chain(self, task_type: str, failed_model: str) -> list[str]:
        """Remaining models to try after failed_model, best-first."""
        chain = self._chain_for(task_type)
        if failed_model in chain:
            chain = chain[chain.index(failed_model) + 1:]
        return [m for m in chain if m != failed_model]

    @staticmethod
    def _safe_connected(adapter: AdapterBase) -> bool:
        try:
            return bool(adapter.is_connected())
        except Exception:
            return False

    # ── recording ─────────────────────────────────────────────────────────
    def record_result(self, model: str, task_type: str, success: bool,
                      latency_ms: int, cost_usd: float) -> None:
        """Feed one outcome into the health tracker."""
        self.health.record(model, task_type, success, latency_ms, cost_usd)

    # ── main entry ────────────────────────────────────────────────────────
    def route(self, task_type: str, payload: dict,
              preferences: dict | None = None) -> RouterResult:
        """
        Execute a task on the best available model, falling through the
        chain on failure. Payload always gets 'task_type' injected so
        multi-role adapters (openai/gemini) know which mode to run.
        Never raises.
        """
        if task_type not in ROUTING_TABLE:
            return RouterResult(model_used="", result=None, success=False,
                                error=f"Unknown task_type: {task_type}")
        payload = dict(payload)
        payload.setdefault("task_type", task_type)

        tried: list[str] = []
        last_error: str | None = None
        total_start = time.monotonic()

        for model in self._chain_for(task_type, preferences):
            adapter = self._get_adapter(model)
            if adapter is None:
                continue  # no adapter built for this model yet
            if not self._safe_connected(adapter):
                continue  # key missing / binary absent — silent skip
            tried.append(model)
            start = time.monotonic()
            try:
                res: AdapterResult = adapter.execute(payload)
            except Exception as e:  # adapters shouldn't raise, but never trust that
                res = AdapterResult(success=False, error=f"{model} raised: {e}")
            latency_ms = res.latency_ms or int((time.monotonic() - start) * 1000)
            self.record_result(model, task_type, res.success, latency_ms, res.cost_usd)
            if res.success:
                return RouterResult(
                    model_used=model, result=res.output,
                    fallbacks_tried=tried[:-1], latency_ms=latency_ms,
                    cost_usd=res.cost_usd, success=True, error=None,
                )
            last_error = res.error or f"{model} failed"
            print(f"{TAG} {task_type}: {model} failed ({last_error}) — trying next",
                  file=sys.stderr)

        total_ms = int((time.monotonic() - total_start) * 1000)
        return RouterResult(
            model_used=tried[-1] if tried else "", result=None,
            fallbacks_tried=tried, latency_ms=total_ms, cost_usd=0.0,
            success=False,
            error=last_error or f"No connected model for {task_type}",
        )

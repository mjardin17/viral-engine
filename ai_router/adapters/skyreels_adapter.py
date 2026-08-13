"""
skyreels_adapter.py — VIDEO_GENERATION via HF Space fffiloni/SkyReels-V2.

Uses HF_TOKEN + gradio_client.
Payload: {"prompt": str, "dest": mp4 path, "reference_image_path": optional str}

NOTE: The Space runs on `cpu-basic` hardware (no GPU). Video diffusion on CPU
is slow — expect many minutes (or longer) per generation. This adapter is a
free, low-stakes fallback, not a fast/high-quality path.

Endpoint signature re-verified 2026-08-09 via client.config dependencies for
api_name="generate_diffusion_forced_video" (23 positional inputs, in order):
  1. prompt (textbox)
  2. input image (image, optional)
  3. video length target (radio) — only choice: "4"
  4. model ID (dropdown) — only choice: "Skywork/SkyReels-V2-DF-1.3B-540P"
  5. resolution (radio, non-interactive) — fixed at "540P"
  6. number of frames (slider, min 17 / max 257 / step 20) — default 97
  7. AR step (number) — default 0
  8. causal attention (checkbox) — default False
  9. causal block size (number) — default 1
  10. base num frames (number) — default 97
  11. overlap history (number, optional) — default None
  12. addnoise condition (number) — default 0
  13. guidance scale (slider) — default 6.0
  14. shift (slider) — default 8.0
  15. inference steps (slider, min 1 / max 100) — default 30
  16. use USP (checkbox) — default False
  17. offload (checkbox) — default True
  18. FPS (slider) — default 24
  19. seed (number, optional) — default None
  20. prompt enhancer (checkbox) — default False
  21. use TeaCache (checkbox) — default True
  22. TeaCache threshold (slider) — default 0.2
  23. use retention steps (checkbox) — default True

Model ID / resolution / video length only have one selectable choice each on
this Space, so the "cheapest" settings are simply the Space's own defaults —
there is no cheaper combination to pick.

KNOWN BLOCKER (as of 2026-08-09): the Space's own config marks this
dependency `"api_visibility": "private"` (same for `set_num_frames`; only
`load_example` is public/"undocumented"). gradio_client 2.6.0 treats
private-visibility dependencies as invalid (`Endpoint.is_valid = False`)
and refuses to call them by api_name *or* fn_index — this is a deliberate
restriction set by the Space author (likely to stop programmatic abuse of
free CPU compute), not a client bug. The call below is correct and will
start working automatically if the author ever flips the endpoint back to
public, but right now every invocation fails fast with a ValueError from
gradio_client itself, before any queueing/inference happens.
"""

from __future__ import annotations

from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

SPACE = "fffiloni/SkyReels-V2"
API_NAME = "/generate_diffusion_forced_video"


class SkyReelsAdapter(AdapterBase):
    """SkyReels-V2 text-to-video via gradio Space (free HF credits)."""

    name = "skyreels"
    capability_score = 0.85
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        if not env("HF_TOKEN"):
            return False
        try:
            import gradio_client  # noqa: F401
            return True
        except ImportError:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False,
                                 error="HF_TOKEN not set or gradio_client not installed")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "skyreels_out.mp4")
        reference_image_path = payload.get("reference_image_path")
        try:
            from gradio_client import Client, handle_file

            def _run():
                client = Client(SPACE, token=env("HF_TOKEN"))
                image_arg = handle_file(reference_image_path) if reference_image_path else None
                return client.predict(
                    prompt,            # 1. prompt
                    image_arg,         # 2. input image (optional)
                    "4",               # 3. video length target (only choice)
                    "Skywork/SkyReels-V2-DF-1.3B-540P",  # 4. model ID (only choice)
                    "540P",            # 5. resolution (fixed)
                    97,                # 6. number of frames
                    0,                 # 7. AR step
                    False,             # 8. causal attention
                    1,                 # 9. causal block size
                    97,                # 10. base num frames
                    None,              # 11. overlap history
                    0,                 # 12. addnoise condition
                    6.0,               # 13. guidance scale
                    8.0,               # 14. shift
                    30,                # 15. inference steps
                    False,             # 16. use USP
                    True,              # 17. offload
                    24,                # 18. FPS
                    None,              # 19. seed
                    False,             # 20. prompt enhancer
                    True,              # 21. use TeaCache
                    0.2,               # 22. TeaCache threshold
                    True,              # 23. use retention steps
                    api_name=API_NAME,
                )

            result, ms = self._timed(_run)
            # Space returns a filepath (or dict with 'video') depending on version
            if isinstance(result, dict):
                result = result.get("video") or result.get("path") or ""
            if isinstance(result, (list, tuple)) and result:
                result = result[0]
            out = Path(str(result))
            if out.exists() and out.stat().st_size > 10_000:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(out.read_bytes())
                return AdapterResult(success=True, output=str(dest), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error=f"SkyReels returned no usable video: {result!r:.120}")
        except ValueError as e:
            if "api_name" in str(e) or "function index" in str(e):
                return AdapterResult(
                    success=False,
                    error=(
                        "skyreels: the Space has marked "
                        f"{API_NAME} as a private (non-public) API endpoint, "
                        "so gradio_client refuses to call it. This is a "
                        "restriction set by the Space author, not a bug in "
                        f"this adapter. Original error: {e}"
                    ),
                )
            return AdapterResult(success=False, error=f"skyreels: {e}")
        except Exception as e:
            return AdapterResult(success=False, error=f"skyreels: {e}")

"""
uploader_adapter.py — PUBLISHING via channel_uploader.py.

STANDING RULE: YouTube uploads require Josh's MANUAL approval. This adapter
therefore NEVER auto-executes an upload — it validates readiness and returns
the exact command for Josh (or an approved mission) to run.
"""

from __future__ import annotations

from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

UPLOADER = BASE_DIR / "channel_uploader.py"
PYTHON_MAIN = Path(r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe")


class UploaderAdapter(AdapterBase):
    """channel_uploader.py front — prepares (never fires) YouTube uploads."""

    name = "channel_uploader"
    capability_score = 1.0
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return UPLOADER.exists()

    def execute(self, payload: dict) -> AdapterResult:
        if not UPLOADER.exists():
            return AdapterResult(success=False,
                                 error=f"channel_uploader.py not found at {UPLOADER}")
        video = Path(payload.get("video_path", ""))
        channel = str(payload.get("channel", "")).upper()
        if not video.exists():
            return AdapterResult(success=False,
                                 error=f"video_path not found: {video}")
        if not channel:
            return AdapterResult(success=False, error="payload missing 'channel'")
        size_mb = video.stat().st_size / 1024 / 1024
        if size_mb < 10:
            return AdapterResult(success=False,
                                 error=f"video only {size_mb:.1f}MB — not upload-ready")
        cmd = (f'"{PYTHON_MAIN}" "{UPLOADER}" --channel {channel} '
               f'--video "{video}" --verify')
        # Standing rule: uploads need Josh's manual approval — return the
        # ready-to-run command instead of executing it.
        return AdapterResult(
            success=True,
            output={"status": "ready_for_manual_approval", "command": cmd,
                    "video": str(video), "size_mb": round(size_mb, 1)},
            meta={"requires_josh_approval": True},
        )

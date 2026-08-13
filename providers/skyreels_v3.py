"""
providers/skyreels_v3.py

SkyReels-V3 (R2V-14B) video-generation provider adapter for Empire OS.

WHAT THIS TARGETS
------------------
SkyReels-V3 R2V-14B ("reference-to-video") is an open-weights model with
native multi-character-reference conditioning (no LoRA training required
to keep a character consistent across shots). There is no public managed
API for it — it must be self-hosted on a rented GPU. This adapter talks to
a **RunPod Serverless** endpoint that the user deploys themselves, using
RunPod's standard async job-queue REST API:

    POST https://api.runpod.ai/v2/{endpoint_id}/run       — submit a job
    GET  https://api.runpod.ai/v2/{endpoint_id}/status/{job_id} — poll it

RunPod was chosen over Vast.ai for this adapter because RunPod Serverless
exposes a clean, stable REST job-queue API (submit → poll → result) with
autoscaling and per-second billing baked in, which maps directly onto this
codebase's async-provider convention (see providers/waterfall.py). Vast.ai
is cheaper for raw GPU-hour rental but is fundamentally an instance
marketplace — there's no first-party serverless job API, so it would need
a bespoke SSH/HTTP wrapper on top before it could look like a provider
here. If the user later prefers Vast.ai, that would be a separate adapter.

ENV VARS
--------
    RUNPOD_API_KEY               RunPod account API key (Settings → API Keys).
    RUNPOD_SKYREELS_ENDPOINT_ID  The Serverless endpoint ID for the deployed
                                  SkyReels-V3 R2V-14B worker (Serverless →
                                  your endpoint → "Endpoint ID").

is_connected() is True only when BOTH are set. Until then every method
degrades gracefully (returns a not_connected/not_supported dict) — nothing
here raises or assumes the account/endpoint exists yet.

WHAT THE USER STILL HAS TO DO (not buildable from here — no GPU, no cloud
account access from this environment)
--------------------------------------------------------------------------
    1. Create a RunPod account and add a payment method.
    2. Containerize SkyReels-V3 R2V-14B: a Docker image with the model
       weights (or weights pulled at cold-start from HF/S3), the RunPod
       Python worker SDK (`runpod` pip package) wrapping inference in a
       `handler(event)` function, and a GPU with enough VRAM for a 14B
       diffusion-transformer video model (target: 1x 48GB+ card, e.g. an
       A6000/L40/A100, depending on the quantization used).
    3. The handler should read `event["input"]` for the same keys this
       adapter sends (prompt, reference_image_b64 or reference_image_url,
       aspect_ratio, duration_sec) and return either
       `{"video_url": "..."}` (if it uploads the result somewhere, e.g. S3
       or RunPod's own storage) or `{"video_base64": "..."}` (if it
       returns the MP4 bytes inline) under RunPod's standard `output` key.
    4. Push the image to a registry RunPod can pull from, deploy it as a
       RunPod Serverless template/endpoint, and copy the resulting
       Endpoint ID into RUNPOD_SKYREELS_ENDPOINT_ID.
    5. Set RUNPOD_API_KEY and RUNPOD_SKYREELS_ENDPOINT_ID in .env.

Until step 4 is done, is_connected() stays False and this provider is a
harmless no-op everywhere it's referenced.

INTEGRATION NOTE
-----------------
This file is intentionally NOT wired into ai_router/router.py or
providers/waterfall.py. That integration is handled separately.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase

RUNPOD_API_BASE = "https://api.runpod.ai/v2"

# RunPod serverless job states → this codebase's terminal-state convention
# (see providers/waterfall.py _TERMINAL_OK / _TERMINAL_FAIL).
_STATE_MAP = {
    "IN_QUEUE": "queued",
    "IN_PROGRESS": "running",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "cancelled",
    "TIMED_OUT": "failed",
}

# Rough self-hosted cost estimate: RunPod serverless GPU billed per-second
# while the worker runs. A 14B ref-to-video job on a high-VRAM card
# (~$0.0008-0.0015/sec typical serverless rate) over a ~90-120s cold/inference
# run lands well under a dollar; kept as a conservative placeholder until
# real numbers are observed from a live endpoint.
ESTIMATED_COST_PER_JOB_USD = 0.35


def _load_env() -> None:
    """Populate os.environ from the repo-root .env (never overrides existing vars)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")


class SkyReelsV3Provider(ProviderBase):
    """
    SkyReels-V3 R2V-14B (reference-to-video) via a self-hosted RunPod
    Serverless endpoint. Video-only provider — see module docstring.
    """

    # ── Capability metadata (mirrors ai_router/adapters/base_adapter.py's
    #    AdapterBase.capability_score / default_cost_usd conventions) ──────
    name: str = "skyreels_v3"
    capability_score: float = 0.9  # native multi-character reference, no LoRA
    default_cost_usd: float = ESTIMATED_COST_PER_JOB_USD
    supports_reference_image: bool = True
    supports_multi_character_reference: bool = True

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("RUNPOD_API_KEY", "")
        self.endpoint_id: str = os.environ.get("RUNPOD_SKYREELS_ENDPOINT_ID", "")

    # ── Connection state ────────────────────────────────────────────────
    def is_connected(self) -> bool:
        """True only if both RUNPOD_API_KEY and RUNPOD_SKYREELS_ENDPOINT_ID are set."""
        return bool(self.api_key) and bool(self.endpoint_id)

    def get_cost_estimate(self, payload: dict | None = None) -> float:
        """Rough per-job USD cost estimate for a self-hosted RunPod job."""
        return self.default_cost_usd

    # ── HTTP helpers (never raise — return {"error": ...} on failure) ──────
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _post(self, path: str, payload: dict, timeout: float = 60.0) -> dict:
        url = f"{RUNPOD_API_BASE}/{self.endpoint_id}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, path: str, timeout: float = 30.0) -> dict:
        url = f"{RUNPOD_API_BASE}/{self.endpoint_id}{path}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def _encode_reference_image(self, reference_image_path: str) -> str | None:
        """Read a local reference image and return a base64 data URI, or None."""
        try:
            path = Path(reference_image_path)
            if not path.is_file():
                return None
            data = path.read_bytes()
            mime = _guess_mime(path)
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception:
            return None

    # ── ProviderBase interface ──────────────────────────────────────────
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """
        Submit a SkyReels-V3 R2V-14B job to the RunPod serverless endpoint.

        Returns {"status": "submitted", "job_id": ..., "provider": "skyreels_v3", "raw": ...}
        on success (matches the waterfall._run_video_provider convention:
        status == "submitted" and a truthy job_id).
        """
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        try:
            job_input: dict = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "duration_sec": duration_sec,
                "model": "skyreels-v3-r2v-14b",
            }
            if reference_image_path:
                data_uri = self._encode_reference_image(reference_image_path)
                if data_uri:
                    job_input["reference_image_b64"] = data_uri
                    # Also send under a "reference_images" list so a multi-
                    # character-capable handler can extend to several refs
                    # without a payload-shape change later.
                    job_input["reference_images"] = [data_uri]
                else:
                    return {
                        "status": "error",
                        "job_id": None,
                        "provider": "skyreels_v3",
                        "raw": f"could not read reference_image_path: {reference_image_path}",
                    }

            result = self._post("/run", {"input": job_input})
            if "error" in result or not result.get("id"):
                return {
                    "status": "error",
                    "job_id": None,
                    "provider": "skyreels_v3",
                    "raw": result,
                }
            return {
                "status": "submitted",
                "job_id": result.get("id"),
                "provider": "skyreels_v3",
                "raw": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "job_id": None,
                "provider": "skyreels_v3",
                "raw": f"unexpected error: {e}",
            }

    def get_job_status(self, job_id: str) -> dict:
        """
        Poll RunPod's /status/{job_id} endpoint and map RunPod job states
        onto this codebase's status convention (see providers/waterfall.py
        _TERMINAL_OK/_TERMINAL_FAIL: "completed"/"failed" etc.).
        """
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        try:
            result = self._get(f"/status/{job_id}")
            if "error" in result:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "output_url": None,
                    "provider": "skyreels_v3",
                    "raw": result,
                }
            runpod_status = str(result.get("status", "")).upper()
            status = _STATE_MAP.get(runpod_status, "running")

            output_url: str | None = None
            output_b64: str | None = None
            if status == "completed":
                output = result.get("output") or {}
                if isinstance(output, dict):
                    output_url = output.get("video_url")
                    output_b64 = output.get("video_base64")
                if not output_url and not output_b64:
                    # Completed but no usable payload — treat as failed so
                    # callers don't hang waiting on a download that'll never work.
                    status = "failed"

            return {
                "job_id": job_id,
                "status": status,
                "output_url": output_url,
                "output_base64": output_b64,
                "provider": "skyreels_v3",
                "raw": result,
            }
        except Exception as e:
            return {
                "job_id": job_id,
                "status": "failed",
                "output_url": None,
                "provider": "skyreels_v3",
                "raw": f"unexpected error: {e}",
            }

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """
        Download a finished clip. Supports both a plain HTTP(S) video_url
        (delegates to ProviderBase.download_clip) and — via
        download_completed_job below — an inline base64 payload.
        """
        return super().download_clip(output_url, dest_path)

    def download_completed_job(self, job_status: dict, dest_path: str | Path) -> bool:
        """
        Convenience helper: given a get_job_status(...) result for a
        completed job, write the resulting video to dest_path regardless
        of whether the RunPod handler returned a URL or inline base64.
        Never raises; returns True only if the file exists and is >10KB.
        """
        dest = Path(dest_path)
        try:
            output_url = job_status.get("output_url")
            if output_url:
                return self.download_clip(str(output_url), dest)

            output_b64 = job_status.get("output_base64")
            if output_b64:
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Tolerate an optional data-URI prefix.
                raw_b64 = output_b64.split(",", 1)[-1] if "," in output_b64 and output_b64.strip().startswith("data:") else output_b64
                data = base64.b64decode(raw_b64)
                if len(data) < 10_000:
                    return False
                dest.write_bytes(data)
                return True

            return False
        except Exception:
            Path(dest_path).unlink(missing_ok=True)
            return False

    # ── Video-only provider: everything else is explicitly unsupported ─────
    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not supported — SkyReels-V3 R2V-14B is used for video only here."""
        return {"status": "not_supported", "message": "SkyReels-V3 is used for video only in Empire OS."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro/Higgsfield handle narration."""
        return {"status": "not_supported", "message": "SkyReels-V3 does not support audio."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "SkyReels-V3 does not support music."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "SkyReels-V3 does not support SFX."}

"""
openai_adapter.py — WRITING / IMAGE_GENERATION / IMAGE_EDITING via OpenAI.

Uses OPENAI_API_KEY (repo .env). Endpoints:
  text        POST https://api.openai.com/v1/chat/completions   (gpt-4o-mini)
  image gen   POST https://api.openai.com/v1/images/generations (gpt-image-1)
  image edit  POST https://api.openai.com/v1/images/edits       (multipart)

Payload keys:
  text tasks:  {"prompt": str}                     → output = text
  image gen:   {"prompt": str, "dest": path}       → output = dest path
  image edit:  {"prompt": str, "image_path": path,
                "mask_path": optional, "dest": path} → output = dest path
"""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.request
import uuid
from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

API_BASE = "https://api.openai.com/v1"
TEXT_TASKS = {"PLANNING", "WRITING", "STORYBOARDING", "PROMPT_CREATION"}


class OpenAIAdapter(AdapterBase):
    """OpenAI: gpt-4o-mini text + gpt-image-1 generation/editing."""

    name = "chatgpt"
    capability_score = 0.90
    default_cost_usd = 0.04  # gpt-image-1 1024x1024 ballpark

    def is_connected(self) -> bool:
        return bool(env("OPENAI_API_KEY"))

    def get_cost_estimate(self, payload: dict) -> float:
        task = payload.get("task_type", "")
        return 0.001 if task in TEXT_TASKS else self.default_cost_usd

    # ── HTTP helpers ──────────────────────────────────────────────────────
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"}

    def _post_json(self, path: str, body: dict, timeout: int = 180) -> dict:
        req = urllib.request.Request(
            f"{API_BASE}{path}", data=json.dumps(body).encode("utf-8"),
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ── task implementations ──────────────────────────────────────────────
    def _text(self, prompt: str) -> AdapterResult:
        out = self._post_json("/chat/completions", {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
        })
        text = out["choices"][0]["message"]["content"]
        return AdapterResult(success=bool(text), output=text, cost_usd=0.001)

    def _image_gen(self, prompt: str, dest: Path) -> AdapterResult:
        out = self._post_json("/images/generations", {
            "model": "gpt-image-1", "prompt": prompt, "size": "1024x1024",
        }, timeout=300)
        b64 = out["data"][0].get("b64_json", "")
        if not b64:
            return AdapterResult(success=False, error="no image data returned")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(b64))
        return AdapterResult(success=True, output=str(dest), cost_usd=self.default_cost_usd)

    def _image_edit(self, prompt: str, image_path: Path,
                    mask_path: Path | None, dest: Path) -> AdapterResult:
        boundary = f"----EmpireOS{uuid.uuid4().hex}"
        parts: list[bytes] = []

        def add_field(field_name: str, value: str) -> None:
            parts.append(
                (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{field_name}"\r\n\r\n{value}\r\n').encode("utf-8"))

        def add_file(field_name: str, path: Path) -> None:
            ctype = mimetypes.guess_type(str(path))[0] or "image/png"
            parts.append(
                (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{field_name}"; filename="{path.name}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n").encode("utf-8"))
            parts.append(path.read_bytes())
            parts.append(b"\r\n")

        add_field("model", "gpt-image-1")
        add_field("prompt", prompt)
        add_field("size", "1024x1024")
        add_file("image", image_path)
        if mask_path is not None and mask_path.exists():
            add_file("mask", mask_path)
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        req = urllib.request.Request(
            f"{API_BASE}/images/edits", data=body,
            headers={**self._headers(),
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        b64 = out["data"][0].get("b64_json", "")
        if not b64:
            return AdapterResult(success=False, error="no edited image returned")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(b64))
        return AdapterResult(success=True, output=str(dest), cost_usd=self.default_cost_usd)

    # ── dispatch ──────────────────────────────────────────────────────────
    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="OPENAI_API_KEY not set")
        task = payload.get("task_type", "")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        try:
            if task in TEXT_TASKS:
                return self._text(prompt)
            dest = Path(payload.get("dest") or "openai_image.png")
            if task == "IMAGE_EDITING":
                image_path = Path(payload.get("image_path", ""))
                if not image_path.exists():
                    return AdapterResult(success=False,
                                         error="IMAGE_EDITING needs existing 'image_path'")
                mask = Path(payload["mask_path"]) if payload.get("mask_path") else None
                return self._image_edit(prompt, image_path, mask, dest)
            return self._image_gen(prompt, dest)
        except Exception as e:
            return AdapterResult(success=False, error=f"openai: {e}")

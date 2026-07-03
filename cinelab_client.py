"""
cinelab_client.py — Python client for the CINELAB /api/claude control plane.

Drop this file anywhere. Set CINELAB_BASE_URL and run:

    python cinelab_client.py autopilot "a 30-second cinematic short about deep-sea bioluminescence"

Or import in another script:

    from cinelab_client import Cinelab
    cl = Cinelab()
    cl.ping()
    ep = cl.create_episode("my_video")
    cl.generate_script("my_video", prompt="...", num_scenes=5)
    cl.generate_all_audio("my_video")
    cl.render_and_wait("my_video")
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

DEFAULT_BASE = os.environ.get(
    "CINELAB_BASE_URL",
    "https://video-generator-423.preview.emergentagent.com",
)


class CinelabError(RuntimeError):
    pass


class Cinelab:
    def __init__(self, base_url: str = DEFAULT_BASE, timeout: int = 120):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    # ---- low-level ----
    def _req(self, method: str, path: str, **kw) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        r = requests.request(method, url, timeout=self.timeout, **kw)
        try:
            data = r.json()
        except Exception as e:
            raise CinelabError(f"Non-JSON response from {url}: {r.status_code} {r.text[:200]}") from e
        if r.status_code >= 500:
            raise CinelabError(f"Server error {r.status_code} on {url}: {data}")
        if isinstance(data, dict) and data.get("ok") is False:
            raise CinelabError(f"{method} {path} failed: {data.get('error')}")
        return data

    # ---- claude control plane ----
    def ping(self) -> Dict[str, Any]:
        return self._req("GET", "/api/claude/ping")

    def list_episodes(self) -> List[Dict[str, Any]]:
        return self._req("GET", "/api/claude/episodes")["episodes"]

    def get_episode(self, episode_id: str) -> Dict[str, Any]:
        return self._req("GET", f"/api/claude/episodes/{episode_id}")["episode"]

    def get_status(self, episode_id: str) -> Dict[str, Any]:
        return self._req("GET", f"/api/claude/episodes/{episode_id}/status")

    def generate_script(self, episode_id, prompt, num_scenes=5, tone=None, replace_scenes=True):
        return self._req("POST", f"/api/claude/episodes/{episode_id}/generate-script",
                         json={"prompt": prompt, "num_scenes": num_scenes,
                               "tone": tone, "replace_scenes": replace_scenes})

    def generate_scene_audio(self, episode_id, scene_number, voice="onyx", model="tts-1", speed=1.0):
        return self._req("POST",
                         f"/api/claude/episodes/{episode_id}/scenes/{scene_number}/generate-audio",
                         json={"voice": voice, "model": model, "speed": speed})

    def generate_all_audio(self, episode_id, voice="onyx", model="tts-1", speed=1.0):
        return self._req("POST", f"/api/claude/episodes/{episode_id}/generate-all-audio",
                         json={"voice": voice, "model": model, "speed": speed})

    def render(self, episode_id):
        return self._req("POST", f"/api/claude/episodes/{episode_id}/render")

    def render_and_wait(self, episode_id, poll_interval=3.0, timeout=600.0):
        """Trigger render and block until it completes or fails."""
        self.render(episode_id)
        start = time.time()
        last = ""
        while time.time() - start < timeout:
            time.sleep(poll_interval)
            st = self.get_status(episode_id)
            prog = st.get("render_progress", "")
            if prog and prog != last:
                print(f"  [{st['render_status']}] {prog}", flush=True)
                last = prog
            if st["render_status"] == "completed":
                return st
            if st["render_status"] == "failed":
                raise CinelabError(f"Render failed: {st.get('render_error')}")
        raise CinelabError(f"Render timed out after {timeout}s")

    # ---- episode CRUD ----
    def create_episode(self, episode_id, title=""):
        url = f"{self.base}/api/episodes"
        r = requests.post(url, json={"episode_id": episode_id, "title": title or episode_id},
                          timeout=self.timeout)
        if r.status_code == 409:
            return self.get_episode(episode_id)
        r.raise_for_status()
        return r.json()

    def upload_image(self, episode_id, scene_number, file_path):
        url = f"{self.base}/api/episodes/{episode_id}/scenes/{scene_number}/image"
        with open(file_path, "rb") as f:
            r = requests.post(url, files={"file": (os.path.basename(file_path), f)},
                              timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def seed_demo_assets(self, episode_id):
        """Pull Unsplash images + TTS for any missing scenes (handy for testing)."""
        r = requests.post(f"{self.base}/api/episodes/{episode_id}/seed-demo", timeout=180)
        r.raise_for_status()
        return r.json()

    def download_video(self, episode_id, out_path):
        url = f"{self.base}/api/episodes/{episode_id}/video"
        r = requests.get(url, timeout=self.timeout, stream=True)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return out_path

    # ---- channel OS ----
    def list_channels(self):
        return self._req("GET", "/api/claude/channels")["channels"]

    def build_channel(self, platform="youtube", hint=None):
        return self._req("POST", "/api/claude/channels/build",
                         json={"platform": platform, "hint": hint})["channel"]

    def generate_channel_videos(self, channel_id, count=4):
        return self._req("POST", f"/api/claude/channels/{channel_id}/generate-videos",
                         json={"count": count})["channel"]


# ============================================================================
# Autopilot — end-to-end pipeline in one command
# ============================================================================
def autopilot(prompt, episode_id=None, num_scenes=5, tone=None,
              voice="onyx", download_to=None, base_url=None):
    """Full pipeline: create → script → seed images → TTS → render → download."""
    cl = Cinelab(base_url or DEFAULT_BASE)
    cl.ping()
    eid = episode_id or f"auto_{int(time.time())}"

    print(f"[1/6] Creating episode '{eid}'...")
    cl.create_episode(eid, title=eid)

    print(f"[2/6] Generating storyboard from prompt...")
    cl.generate_script(eid, prompt=prompt, num_scenes=num_scenes, tone=tone)

    print(f"[3/6] Seeding demo images (Unsplash)...")
    cl.seed_demo_assets(eid)

    print(f"[4/6] Generating any remaining TTS audio (voice={voice})...")
    cl.generate_all_audio(eid, voice=voice)

    print(f"[5/6] Rendering... this takes ~30-60s")
    st = cl.render_and_wait(eid)

    out_path = st.get("output_path")
    size_mb = (st.get("output_size_bytes", 0) or 0) / 1024 / 1024
    print(f"[6/6] DONE → {out_path} ({size_mb:.2f} MB)")

    if download_to:
        local = cl.download_video(eid, download_to)
        print(f"      Downloaded local copy → {local}")
    return st


# ============================================================================
# CLI
# ============================================================================
def _cli():
    ap = argparse.ArgumentParser(description="Cinelab Claude control-plane client")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping")
    sub.add_parser("episodes")

    p_get = sub.add_parser("get"); p_get.add_argument("episode_id")
    p_st  = sub.add_parser("status"); p_st.add_argument("episode_id")

    p_ap = sub.add_parser("autopilot")
    p_ap.add_argument("prompt")
    p_ap.add_argument("--episode-id", default=None)
    p_ap.add_argument("--scenes", type=int, default=5)
    p_ap.add_argument("--tone", default=None)
    p_ap.add_argument("--voice", default="onyx")
    p_ap.add_argument("--download", default=None)

    p_ch = sub.add_parser("build-channel")
    p_ch.add_argument("--platform", default="youtube")
    p_ch.add_argument("--hint", default=None)

    sub.add_parser("channels")

    p_cv = sub.add_parser("channel-videos")
    p_cv.add_argument("channel_id")
    p_cv.add_argument("--count", type=int, default=4)

    args = ap.parse_args()
    cl = Cinelab()

    if args.cmd == "ping":
        print(json.dumps(cl.ping(), indent=2))
    elif args.cmd == "episodes":
        for e in cl.list_episodes():
            print(f"  {e['episode_id']:30s}  scenes={e['scene_count']}  "
                  f"status={e['render_status']:10s}  has_output={e['has_output']}")
    elif args.cmd == "get":
        print(json.dumps(cl.get_episode(args.episode_id), indent=2))
    elif args.cmd == "status":
        print(json.dumps(cl.get_status(args.episode_id), indent=2))
    elif args.cmd == "autopilot":
        autopilot(args.prompt, episode_id=args.episode_id, num_scenes=args.scenes,
                  tone=args.tone, voice=args.voice, download_to=args.download)
    elif args.cmd == "build-channel":
        print(json.dumps(cl.build_channel(args.platform, args.hint), indent=2))
    elif args.cmd == "channels":
        for c in cl.list_channels():
            print(f"  {c['id']}  {c['channel_name']:30s}  "
                  f"[{c['platform']}]  videos={c['video_count']}")
    elif args.cmd == "channel-videos":
        ch = cl.generate_channel_videos(args.channel_id, args.count)
        print(f"Generated {len(ch.get('videos', []))} videos for {ch.get('channel_name')}")
        for v in ch.get("videos", []):
            print(f"  #{v['video_number']:2d}  {v['title']}")


if __name__ == "__main__":
    try:
        _cli()
    except CinelabError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

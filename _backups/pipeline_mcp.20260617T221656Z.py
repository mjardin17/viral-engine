"""
Claude Desktop MCP config:
{
  "mcpServers": {
    "video-pipeline": {
      "command": "python",
      "args": ["C:/Users/jjard/claude/video-bot-pipeline/pipeline_mcp.py"],
      "env": {}
    }
  }
}
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
BASE_DIR = Path("C:/Users/jjard/claude/video-bot-pipeline")
PROMPTS_DIR = BASE_DIR / "prompts"
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"
mcp = FastMCP("Video Pipeline MCP")
def _safe_json_load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
def _episode_json_files() -> List[Path]:
    if not PROMPTS_DIR.exists():
        return []
    return sorted(PROMPTS_DIR.rglob("*.json"))
def _find_episode_file(episode_id: str) -> Optional[Path]:
    for path in _episode_json_files():
        try:
            data = _safe_json_load(path)
            if data.get("episode_id") == episode_id:
                return path
        except Exception:
            continue
    return None
def _run_streamed(cmd: List[str]) -> Dict[str, Any]:
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    lines: List[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        print(line, flush=True)
    code = proc.wait()
    return {"ok": code == 0, "returncode": code, "stdout": "\n".join(lines)}
@mcp.tool
def list_episodes() -> Dict[str, Any]:
    """Scan prompts/ recursively and return all episode IDs, titles, and channels."""
    try:
        files = _episode_json_files()
        episodes = []
        seen = set()
        for path in files:
            try:
                data = _safe_json_load(path)
            except Exception:
                continue
            episode_id = data.get("episode_id")
            if not episode_id or episode_id in seen:
                continue
            seen.add(episode_id)
            episodes.append(
                {
                    "episode_id": episode_id,
                    "title": data.get("title"),
                    "channel": data.get("channel"),
                    "path": str(path),
                }
            )
        return {"ok": True, "count": len(episodes), "episodes": episodes}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def get_episode(episode_id: str) -> Dict[str, Any]:
    """Return the full episode JSON for a given episode ID."""
    try:
        path = _find_episode_file(episode_id)
        if path is None:
            return {"ok": False, "error": f"Episode not found: {episode_id}"}
        return {"ok": True, "episode": _safe_json_load(path), "path": str(path)}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def dry_run(episode_id: str) -> Dict[str, Any]:
    """Run voice_video_pipeline.py --dry-run for the episode and return stdout."""
    try:
        cmd = ["python", "voice_video_pipeline.py", "--episode", episode_id, "--dry-run"]
        return _run_streamed(cmd)
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def generate_images(
    episode_id: str,
    scenes: Optional[List[int]] = None,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """Run generate_images.py for an episode, optionally limiting to specific scenes."""
    try:
        cmd = ["python", "generate_images.py", "--episode", episode_id]
        if scenes:
            # generate_images.py uses nargs="+" so each scene is a separate arg
            cmd += ["--scenes"] + [str(s) for s in scenes]
        if skip_existing:
            cmd += ["--skip-existing"]
        return _run_streamed(cmd)
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def render_episode(
    episode_id: str,
    music: Optional[str] = None,
    use_windows_tts: bool = False,
) -> Dict[str, Any]:
    """Render the episode using voice_video_pipeline.py or make_clip_windows.py."""
    try:
        if use_windows_tts:
            cmd = ["python", "make_clip_windows.py", "--episode", episode_id]
            if music:
                cmd += ["--music", music]
        else:
            cmd = ["python", "voice_video_pipeline.py", "--episode", episode_id]
            if music:
                cmd += ["--music", music]
        return _run_streamed(cmd)
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def get_output_status(episode_id: str) -> Dict[str, Any]:
    """Check for output/{episode_id}_final.mp4 or output/{episode_id}_standalone.mp4."""
    try:
        candidates = [
            OUTPUT_DIR / f"{episode_id}_final.mp4",
            OUTPUT_DIR / f"{episode_id}_standalone.mp4",
        ]
        found = []
        for path in candidates:
            if path.exists():
                found.append(
                    {
                        "path": str(path),
                        "size_bytes": path.stat().st_size,
                    }
                )
        return {"ok": True, "found": bool(found), "outputs": found}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@mcp.tool
def list_images(episode_id: str) -> Dict[str, Any]:
    """Return which scene images exist vs are missing for the given episode."""
    try:
        ep = get_episode(episode_id)
        if not ep.get("ok"):
            return ep
        scenes = ep["episode"].get("scenes", [])
        image_status = []
        for scene in scenes:
            n = int(scene.get("scene_number"))
            path = IMAGES_DIR / episode_id / f"scene_{n:02d}.png"
            image_status.append(
                {
                    "scene_number": n,
                    "path": str(path),
                    "exists": path.exists(),
                }
            )
        return {"ok": True, "episode_id": episode_id, "images": image_status}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"FileNotFoundError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
if __name__ == "__main__":
    mcp.run(transport="stdio")

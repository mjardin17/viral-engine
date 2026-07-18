"""
free_tool_scout.py — Empire OS free-tool discovery brain.

Finds ZERO-SIGNUP / no-auth AI + media APIs, tests them live, and keeps a
running ledger in free_tools_discovered.json so the council (bot_13) can
surface new tools worth wiring into the pipeline.

Sources scanned:
  1. Known Empire OS zero-signup endpoints (regression check — are the tools
     we already wired still alive?)
  2. github.com/public-apis/public-apis README — Machine Learning +
     related sections, entries with "Auth: No"
  3. github.com/sindresorhus/awesome-free-services readme — AI-flavored links

Every candidate gets a live HTTP test (10s timeout). Results:

  free_tools_discovered.json
  {
    "last_checked": "2026-07-18",
    "working": [{"name", "url", "type", "tested_ms", "source"}],
    "broken":  [...],
    "new_since_last_check": ["name", ...]
  }

CLI:
  python free_tool_scout.py           # run a discovery scan
  python free_tool_scout.py --report  # print last results without re-scanning
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "free_tools_discovered.json"
TAG = "[tool_scout]"
UA = {"User-Agent": "EmpireOS-ToolScout/1.0"}
TEST_TIMEOUT_SEC = 10
MAX_LIST_CANDIDATES = 25  # cap per source list — keep a scan under ~5 min

PUBLIC_APIS_URL = ("https://raw.githubusercontent.com/public-apis/"
                   "public-apis/master/README.md")
AWESOME_FREE_URL = ("https://raw.githubusercontent.com/sindresorhus/"
                    "awesome-free-services/main/readme.md")

# Sections of public-apis worth mining for pipeline-relevant tools.
INTERESTING_SECTIONS = ("machine learning", "art & design", "photography",
                        "music", "text analysis", "video", "open data")

# ── Known Empire OS zero-signup endpoints (regression checks) ─────────────────
# (name, test_url, type) — a 200/OK on test_url means the tool is alive.
KNOWN_TOOLS: tuple[tuple[str, str, str], ...] = (
    ("pollinations", "https://image.pollinations.ai/prompt/test?width=64&height=64", "image"),
    ("lexica", "https://lexica.art/api/v1/search?q=battle", "image"),
    ("wikiart", "https://www.wikiart.org/en/search/battle/1?json=2", "image"),
    ("openverse", "https://api.openverse.org/v1/images/?q=battle&page_size=1", "image"),
    ("ai_horde", "https://stablehorde.net/api/v2/status/heartbeat", "image"),
    ("picsum", "https://picsum.photos/64/64", "image"),
    ("freepd", "https://freepd.com/music/Redline.mp3", "audio"),
    ("wikimedia_commons",
     "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search"
     "&srsearch=battle&srlimit=1", "image"),
)


def _fetch_text(url: str, timeout: int = 30) -> str:
    """GET a URL as text; returns "" on any failure."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"{TAG} fetch failed {url}: {e}", file=sys.stderr)
        return ""


def _guess_type(name: str, description: str) -> str:
    """Rough tool-type classification from its name/description."""
    text = f"{name} {description}".lower()
    if any(w in text for w in ("image", "photo", "art", "picture", "diffusion", "vision")):
        return "image"
    if any(w in text for w in ("audio", "music", "speech", "voice", "sound", "tts")):
        return "audio"
    if any(w in text for w in ("video", "film", "movie")):
        return "video"
    return "text"


# ── Source parsers ────────────────────────────────────────────────────────────
def parse_public_apis(markdown: str) -> list[dict]:
    """
    Parse public-apis README tables. Rows look like:
      | [Name](https://url) | Description | `apiKey` / No | Yes | Yes |
    Keeps only rows from interesting sections whose Auth column is "No".
    """
    found: list[dict] = []
    section = ""
    for line in markdown.splitlines():
        heading = re.match(r"^#{2,3}\s+(.*)", line)
        if heading:
            section = heading.group(1).strip().lower()
            continue
        if not line.startswith("|") or not any(s in section for s in INTERESTING_SECTIONS):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cells[0])
        if not link:
            continue
        auth = cells[2].strip("`").strip().lower()
        if auth not in ("no", "none", ""):
            continue  # needs a key/signup — not our kind of tool
        name, url = link.group(1), link.group(2)
        found.append({
            "name": name,
            "url": url,
            "type": _guess_type(name, cells[1]),
            "source": f"public-apis/{section}",
        })
    return found


def parse_awesome_free(markdown: str) -> list[dict]:
    """
    Parse awesome-free-services for AI-flavored entries:
      - [Name](url) - description
    Kept when the section or description smells like AI/ML and mentions a
    free tier / no auth.
    """
    found: list[dict] = []
    section = ""
    ai_words = ("ai", "machine learning", "ml", "artificial intelligence",
                "llm", "image", "speech")
    for line in markdown.splitlines():
        heading = re.match(r"^#{2,3}\s+(.*)", line)
        if heading:
            section = heading.group(1).strip().lower()
            continue
        link = re.match(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)]+)\)\s*[-—:]?\s*(.*)", line)
        if not link:
            continue
        name, url, desc = link.group(1), link.group(2), link.group(3)
        blob = f"{section} {name} {desc}".lower()
        if not any(w in blob for w in ai_words):
            continue
        if not any(w in blob for w in ("free", "no auth", "no signup", "no key")):
            continue
        found.append({
            "name": name,
            "url": url,
            "type": _guess_type(name, desc),
            "source": f"awesome-free-services/{section or 'root'}",
        })
    return found


# ── Live testing ──────────────────────────────────────────────────────────────
def test_tool(url: str) -> tuple[bool, int]:
    """
    Hit `url` with a GET (10s timeout). Returns (works, response_time_ms).
    Any HTTP status < 500 counts as alive — 4xx still proves the host and
    API surface exist (we may just need different params).
    """
    start = time.monotonic()
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TEST_TIMEOUT_SEC) as resp:
            resp.read(2048)  # touch the body, don't download the world
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        return False, int((time.monotonic() - start) * 1000)
    ms = int((time.monotonic() - start) * 1000)
    return code < 500, ms


# ── Scan orchestration ────────────────────────────────────────────────────────
def load_results() -> dict:
    """Load the last scan results (empty structure if none)."""
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_checked": "", "working": [], "broken": [],
            "new_since_last_check": []}


def run_scan() -> dict:
    """Full discovery scan: gather candidates, live-test, save + return results."""
    previous = load_results()
    previously_known = {t["name"] for t in
                        previous.get("working", []) + previous.get("broken", [])}

    candidates: list[dict] = [
        {"name": name, "url": url, "type": kind, "source": "empire-known"}
        for name, url, kind in KNOWN_TOOLS
    ]

    print(f"{TAG} fetching public-apis list...")
    md = _fetch_text(PUBLIC_APIS_URL)
    from_public = parse_public_apis(md)[:MAX_LIST_CANDIDATES]
    print(f"{TAG}   {len(from_public)} no-auth candidates in interesting sections")
    candidates += from_public

    print(f"{TAG} fetching awesome-free-services list...")
    md = _fetch_text(AWESOME_FREE_URL)
    from_awesome = parse_awesome_free(md)[:MAX_LIST_CANDIDATES]
    print(f"{TAG}   {len(from_awesome)} AI/free candidates")
    candidates += from_awesome

    # De-dupe by name (first occurrence wins — known tools take precedence).
    seen: set[str] = set()
    unique: list[dict] = []
    for c in candidates:
        key = c["name"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    working: list[dict] = []
    broken: list[dict] = []
    print(f"{TAG} live-testing {len(unique)} tools ({TEST_TIMEOUT_SEC}s timeout each)...")
    for c in unique:
        ok, ms = test_tool(c["url"])
        record = {"name": c["name"], "url": c["url"], "type": c["type"],
                  "tested_ms": ms, "source": c["source"]}
        (working if ok else broken).append(record)
        print(f"{TAG}   {'✅' if ok else '❌'} {c['name']:<30} {ms:>6}ms  ({c['source']})")

    new_names = sorted({t["name"] for t in working} - previously_known)
    results = {
        "last_checked": date.today().isoformat(),
        "working": working,
        "broken": broken,
        "new_since_last_check": new_names,
    }
    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"{TAG} saved → {RESULTS_FILE}")
    return results


def print_report(results: dict) -> None:
    """Human-readable DISCOVERY REPORT for a results dict."""
    working = results.get("working", [])
    broken = results.get("broken", [])
    new = results.get("new_since_last_check", [])

    print("\n" + "=" * 62)
    print("  FREE TOOL DISCOVERY REPORT")
    print(f"  last checked: {results.get('last_checked', 'never')}")
    print("=" * 62)

    print(f"\nNEW since last run ({len(new)}):")
    for name in new:
        print(f"  + {name}")
    if not new:
        print("  (none)")

    print(f"\nWORKING ({len(working)}):")
    for t in sorted(working, key=lambda t: t["tested_ms"]):
        print(f"  ✅ {t['name']:<30} {t['type']:<6} {t['tested_ms']:>6}ms  {t['source']}")

    print(f"\nBROKEN ({len(broken)}):")
    for t in broken:
        print(f"  ❌ {t['name']:<30} {t['type']:<6} {t['source']}")

    # Top recommendation: fastest working tool not already wired in.
    wired = {name for name, _, _ in KNOWN_TOOLS}
    unwired = [t for t in working if t["name"] not in wired]
    print("\nTOP RECOMMENDATION:")
    if unwired:
        best = min(unwired, key=lambda t: t["tested_ms"])
        print(f"  Wire in next → {best['name']} ({best['type']}, "
              f"{best['tested_ms']}ms, {best['url']})")
    else:
        print("  Everything working is already wired in. 👑")
    print("=" * 62 + "\n")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Empire OS free-tool discovery brain")
    parser.add_argument("--report", action="store_true",
                        help="Print last results without re-scanning")
    args = parser.parse_args()
    results = load_results() if args.report else run_scan()
    print_report(results)


if __name__ == "__main__":
    main()

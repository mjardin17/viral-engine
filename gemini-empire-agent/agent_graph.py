"""
gemini-empire-agent/agent_graph.py
Empire OS Agent Graph — LangGraph + real pipeline tools
Claude is the CTO brain. This agent handles all light/automated work.

TASK DIVISION:
  Claude       → Architecture, code, strategy, script writing
  Goose        → Orchestrator: runs pipeline_run.py end-to-end
  This agent   → Light work: council, health checks, ads, git sync, status reports
  Council bots → Self-healing: broken clips, stubs, image repair, render queue
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from core.self_healing import SelfHealingSystem

# ── Root of the repo ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()

healing = SelfHealingSystem()


class AgentState(TypedDict):
    messages: List[str]
    task: str
    result: Optional[str]
    error: Optional[str]
    next: str


# ──────────────────────────────────────────────────────────────────────────────
# TOOL FUNCTIONS (the real work)
# ──────────────────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> str:
    """Run a subprocess and return stdout+stderr as a string."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"Command failed (rc={result.returncode}): {output[-500:]}")
    return output.strip()


def tool_run_council() -> str:
    """Run all 9 council bots — health check + self-heal the pipeline."""
    return _run(["python", "council/council.py"], timeout=600)


def tool_health_check() -> dict:
    """Check renders/ for broken, short, or missing finals."""
    renders = ROOT / "renders"
    report = {"ok": [], "broken": [], "short": [], "missing": []}

    expected = [f"GG_EP{str(i).zfill(3)}_final.mp4" for i in range(1, 12)]
    for ep in expected:
        path = renders / ep
        if not path.exists():
            report["missing"].append(ep)
        elif path.stat().st_size < 1_000_000:  # < 1MB = broken
            report["broken"].append(ep)
        elif path.stat().st_size < 50_000_000:  # < 50MB = suspiciously short
            report["short"].append(ep)
        else:
            report["ok"].append(ep)

    return report


def tool_generate_ads(website_url: str = "https://jardins-outpost.pages.dev") -> str:
    """Generate this week's ad schedule using empire_ads.py."""
    return _run(
        [sys.executable, "empire_ads.py", "--website", website_url],
        timeout=180,
    )


def tool_render_episode(channel: str = "gg", episode: Optional[str] = None) -> str:
    """Run pipeline_run.py for a single episode (skip upload — Josh approves)."""
    cmd = [sys.executable, "pipeline_run.py", "--channel", channel, "--skip-publish"]
    if episode:
        cmd += ["--episode", episode]
    return _run(cmd, timeout=3600)


def tool_git_sync(message: str = "auto: agent sync") -> str:
    """Pull latest, then push any changes."""
    pull = _run(["git", "pull", "origin", "main"])
    status = _run(["git", "status", "--short"])
    if not status:
        return f"Pull OK. Nothing to push.\n{pull}"
    _run(["git", "add", "-A"])
    _run(["git", "commit", "-m", f"[AGENT] {message}"])
    push = _run(["git", "push", "origin", "main"])
    return f"Synced.\n{pull}\n{push}"


def tool_council_status() -> dict:
    """Read the latest council state files."""
    state_dir = ROOT / "council" / "state"
    reports = {}
    if state_dir.exists():
        for f in state_dir.glob("*.json"):
            try:
                reports[f.stem] = json.loads(f.read_text())
            except Exception:
                reports[f.stem] = "unreadable"
    guardian = ROOT / "guardian_report.json"
    if guardian.exists():
        try:
            reports["guardian"] = json.loads(guardian.read_text())
        except Exception:
            pass
    return reports


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER — decides which tool node to call
# ──────────────────────────────────────────────────────────────────────────────

TASK_ROUTES = {
    "council":      "run_council",
    "health":       "health_check",
    "ads":          "generate_ads",
    "render":       "render_episode",
    "git":          "git_sync",
    "sync":         "git_sync",
    "status":       "council_status",
}


def supervisor_node(state: AgentState) -> AgentState:
    task = (state.get("task") or " ".join(state.get("messages", []))).lower()
    for keyword, route in TASK_ROUTES.items():
        if keyword in task:
            return {**state, "next": route}
    return {**state, "next": "health_check"}  # default: health check


# ──────────────────────────────────────────────────────────────────────────────
# TOOL NODES
# ──────────────────────────────────────────────────────────────────────────────

def node_run_council(state: AgentState) -> AgentState:
    try:
        out = tool_run_council()
        return {**state, "result": out, "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "run_council")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


def node_health_check(state: AgentState) -> AgentState:
    try:
        report = tool_health_check()
        return {**state, "result": json.dumps(report, indent=2), "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "health_check")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


def node_generate_ads(state: AgentState) -> AgentState:
    try:
        out = tool_generate_ads()
        return {**state, "result": out, "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "generate_ads")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


def node_render_episode(state: AgentState) -> AgentState:
    try:
        task = state.get("task", "")
        # parse optional episode from task string e.g. "render GG_EP012"
        episode = None
        for word in task.upper().split():
            if word.startswith("GG_EP") or word.startswith("IL_EP") or word.startswith("LO_EP"):
                episode = word
        out = tool_render_episode(episode=episode)
        return {**state, "result": out, "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "render_episode")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


def node_git_sync(state: AgentState) -> AgentState:
    try:
        out = tool_git_sync()
        return {**state, "result": out, "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "git_sync")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


def node_council_status(state: AgentState) -> AgentState:
    try:
        report = tool_council_status()
        return {**state, "result": json.dumps(report, indent=2), "next": "END"}
    except Exception as e:
        action = healing.report_error(e, "council_status")
        return {**state, "error": str(e), "result": f"Self-healing: {action}", "next": "END"}


# ──────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ──────────────────────────────────────────────────────────────────────────────

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor",      supervisor_node)
    workflow.add_node("run_council",     node_run_council)
    workflow.add_node("health_check",    node_health_check)
    workflow.add_node("generate_ads",    node_generate_ads)
    workflow.add_node("render_episode",  node_render_episode)
    workflow.add_node("git_sync",        node_git_sync)
    workflow.add_node("council_status",  node_council_status)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda s: s["next"],
        {
            "run_council":    "run_council",
            "health_check":   "health_check",
            "generate_ads":   "generate_ads",
            "render_episode": "render_episode",
            "git_sync":       "git_sync",
            "council_status": "council_status",
        }
    )

    for node in ["run_council", "health_check", "generate_ads",
                 "render_episode", "git_sync", "council_status"]:
        workflow.add_edge(node, END)

    print("EmpireForge Agent Graph — tools wired and ready")
    return workflow.compile()

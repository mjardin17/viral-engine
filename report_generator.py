"""
report_generator.py — Empire OS pipeline engineering report.

Collects everything that happened during one empire_render.py run (models
used, routing decisions, fallbacks, quality scores, errors) and writes
PIPELINE_ENGINEERING_REPORT.md at the repo root.

Usage:
    report = ReportGenerator(run_id, episode_id, channel)
    report.log_model_used("NARRATION", "kokoro", 3200, 0.0)
    ...
    path = report.generate()
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
REPORT_PATH: Path = BASE_DIR / "PIPELINE_ENGINEERING_REPORT.md"


class ReportGenerator:
    """Accumulates run events, renders them as a markdown engineering report."""

    def __init__(self, run_id: str, episode_id: str, channel: str) -> None:
        self.run_id = run_id
        self.episode_id = episode_id
        self.channel = channel
        self.started_at = datetime.now()
        self.models_used: list[dict] = []
        self.routing_decisions: list[dict] = []
        self.fallbacks: list[dict] = []
        self.quality_scores: list[dict] = []
        self.errors: list[dict] = []

    # ── logging API ───────────────────────────────────────────────────────
    def log_model_used(self, task_type: str, model: str,
                       latency_ms: int, cost_usd: float) -> None:
        self.models_used.append({
            "task_type": task_type, "model": model,
            "latency_ms": latency_ms, "cost_usd": cost_usd,
            "at": datetime.now().isoformat(timespec="seconds"),
        })

    def log_routing_decision(self, task_type: str, chosen: str,
                             rejected: list[str], reason: str) -> None:
        self.routing_decisions.append({
            "task_type": task_type, "chosen": chosen,
            "rejected": list(rejected), "reason": reason,
        })

    def log_fallback(self, task_type: str, failed_model: str,
                     fallback_model: str, reason: str) -> None:
        self.fallbacks.append({
            "task_type": task_type, "failed_model": failed_model,
            "fallback_model": fallback_model, "reason": reason,
        })

    def log_quality_score(self, stage: str, score: float, details: dict) -> None:
        self.quality_scores.append({
            "stage": stage, "score": score, "details": dict(details),
        })

    def log_error(self, stage: str, error: str, recovered: bool) -> None:
        self.errors.append({
            "stage": stage, "error": error, "recovered": recovered,
        })

    # ── report generation ─────────────────────────────────────────────────
    def _recommendations(self) -> list[str]:
        """Derive optimization recommendations from this run's data."""
        recs: list[str] = []
        total_cost = sum(m["cost_usd"] for m in self.models_used)
        if total_cost > 1.0:
            recs.append(f"Run cost ${total_cost:.2f} — check whether free "
                        f"providers can absorb the paid calls.")
        slow = [m for m in self.models_used if m["latency_ms"] > 120_000]
        for m in slow[:3]:
            recs.append(f"{m['model']} took {m['latency_ms'] / 1000:.0f}s on "
                        f"{m['task_type']} — consider reordering the chain.")
        flaky_tasks = {f["task_type"] for f in self.fallbacks}
        for t in sorted(flaky_tasks):
            count = sum(1 for f in self.fallbacks if f["task_type"] == t)
            if count >= 3:
                recs.append(f"{t} needed {count} fallbacks — the primary model "
                            f"for this task is unreliable right now.")
        low_q = [q for q in self.quality_scores if q["score"] < 0.5]
        for q in low_q[:3]:
            recs.append(f"Stage {q['stage']} scored {q['score']:.2f} — "
                        f"inspect before upload.")
        unrecovered = [e for e in self.errors if not e["recovered"]]
        if unrecovered:
            recs.append(f"{len(unrecovered)} unrecovered error(s) — "
                        f"episode may be incomplete.")
        if not recs:
            recs.append("Clean run — no optimizations flagged.")
        return recs

    def generate(self) -> str:
        """Write PIPELINE_ENGINEERING_REPORT.md; return its path."""
        elapsed = datetime.now() - self.started_at
        total_cost = sum(m["cost_usd"] for m in self.models_used)
        lines: list[str] = [
            "# Pipeline Engineering Report",
            "",
            f"- **Run ID:** {self.run_id}",
            f"- **Episode:** {self.episode_id}",
            f"- **Channel:** {self.channel}",
            f"- **Started:** {self.started_at.isoformat(timespec='seconds')}",
            f"- **Elapsed:** {elapsed}",
            f"- **Total cost:** ${total_cost:.4f}",
            "",
            "## Models Used",
            "",
        ]
        if self.models_used:
            lines += ["| Task | Model | Latency (ms) | Cost (USD) |",
                      "|------|-------|-------------:|-----------:|"]
            lines += [f"| {m['task_type']} | {m['model']} | {m['latency_ms']} "
                      f"| {m['cost_usd']:.4f} |" for m in self.models_used]
        else:
            lines.append("_No routed model calls this run._")

        lines += ["", "## Routing Decisions", ""]
        if self.routing_decisions:
            for d in self.routing_decisions:
                rej = ", ".join(d["rejected"]) or "none"
                lines.append(f"- **{d['task_type']}** → `{d['chosen']}` "
                             f"(rejected: {rej}) — {d['reason']}")
        else:
            lines.append("_No routing decisions logged._")

        lines += ["", "## Fallbacks", ""]
        if self.fallbacks:
            for f in self.fallbacks:
                lines.append(f"- **{f['task_type']}**: `{f['failed_model']}` failed "
                             f"→ `{f['fallback_model']}` — {f['reason']}")
        else:
            lines.append("_No fallbacks needed._")

        lines += ["", "## Performance Table", ""]
        by_model: dict[str, list[dict]] = {}
        for m in self.models_used:
            by_model.setdefault(m["model"], []).append(m)
        if by_model:
            lines += ["| Model | Calls | Avg latency (ms) | Total cost |",
                      "|-------|------:|-----------------:|-----------:|"]
            for model, calls in sorted(by_model.items()):
                avg = sum(c["latency_ms"] for c in calls) // len(calls)
                cost = sum(c["cost_usd"] for c in calls)
                lines.append(f"| {model} | {len(calls)} | {avg} | ${cost:.4f} |")
        else:
            lines.append("_No performance data._")

        lines += ["", "## Errors & Recoveries", ""]
        if self.errors:
            for e in self.errors:
                icon = "recovered" if e["recovered"] else "NOT RECOVERED"
                lines.append(f"- [{icon}] **{e['stage']}**: {e['error']}")
        else:
            lines.append("_No errors._")

        lines += ["", "## Quality Scores", ""]
        if self.quality_scores:
            for q in self.quality_scores:
                lines.append(f"- **{q['stage']}**: {q['score']:.2f} — "
                             f"{q['details']}")
        else:
            lines.append("_No quality scores logged._")

        lines += ["", "## Optimization Recommendations", ""]
        lines += [f"- {r}" for r in self._recommendations()]
        lines.append("")

        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        return str(REPORT_PATH)

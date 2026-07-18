"""
ai_router/model_health.py — Empire OS model performance tracker.

Records every routed call (success, latency, cost) per model+task and scores
models so the router can prefer what actually works on Josh's machine.

Score formula:
    (success_rate * 0.5)
  + (1 / (avg_latency_ms/1000 + 1) * 0.3)
  + (1 / (avg_cost + 0.01) * 0.2)   # cost term capped at 1.0 so free != infinite

Storage: model_health.json in repo root (gitignored — runtime state, not code).
Thread-safe; never raises on corrupt/missing state.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent
HEALTH_PATH: Path = BASE_DIR / "model_health.json"

_lock = threading.Lock()


class ModelHealth:
    """Persistent per-model, per-task performance stats."""

    def __init__(self, path: Path = HEALTH_PATH) -> None:
        self.path = path
        self._data: dict = self._load()

    # ── persistence ───────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            if self.path.exists():
                return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            pass  # health tracking must never break a render

    # ── recording ─────────────────────────────────────────────────────────
    def record(self, model: str, task_type: str, success: bool,
               latency_ms: int, cost_usd: float = 0.0) -> None:
        """Record one call outcome for model on task_type."""
        with _lock:
            entry = self._data.setdefault(model, {}).setdefault(task_type, {
                "calls": 0, "successes": 0,
                "total_latency_ms": 0, "total_cost_usd": 0.0,
                "last_used": None, "last_error_at": None,
            })
            entry["calls"] += 1
            if success:
                entry["successes"] += 1
            else:
                entry["last_error_at"] = datetime.now().isoformat()
            entry["total_latency_ms"] += max(0, int(latency_ms))
            entry["total_cost_usd"] += max(0.0, float(cost_usd))
            entry["last_used"] = datetime.now().isoformat()
            self._save()

    # ── scoring ───────────────────────────────────────────────────────────
    @staticmethod
    def _score_entry(entry: dict) -> float:
        calls = entry.get("calls", 0)
        if calls <= 0:
            return 0.5  # unknown model — neutral score
        success_rate = entry.get("successes", 0) / calls
        avg_latency_ms = entry.get("total_latency_ms", 0) / calls
        avg_cost = entry.get("total_cost_usd", 0.0) / calls
        latency_term = 1.0 / (avg_latency_ms / 1000.0 + 1.0)
        cost_term = min(1.0, 1.0 / (avg_cost + 0.01))
        return (success_rate * 0.5) + (latency_term * 0.3) + (cost_term * 0.2)

    def get_score(self, model: str) -> float:
        """Overall 0.0–1.0 score for a model across all task types."""
        tasks = self._data.get(model)
        if not tasks:
            return 0.5  # never used — neutral, don't punish new models
        scores = [self._score_entry(e) for e in tasks.values()]
        return sum(scores) / len(scores) if scores else 0.5

    def get_task_score(self, model: str, task_type: str) -> float:
        """0.0–1.0 score for a model on one specific task type."""
        entry = (self._data.get(model) or {}).get(task_type)
        if not entry:
            return self.get_score(model)
        return self._score_entry(entry)

    # ── reporting ─────────────────────────────────────────────────────────
    def get_report(self) -> dict:
        """Full stats report: per model → per task → calls/rates/averages."""
        report: dict = {}
        for model, tasks in self._data.items():
            report[model] = {"overall_score": round(self.get_score(model), 3), "tasks": {}}
            for task, e in tasks.items():
                calls = e.get("calls", 0) or 1
                report[model]["tasks"][task] = {
                    "calls": e.get("calls", 0),
                    "success_rate": round(e.get("successes", 0) / calls, 3),
                    "avg_latency_ms": int(e.get("total_latency_ms", 0) / calls),
                    "avg_cost_usd": round(e.get("total_cost_usd", 0.0) / calls, 4),
                    "score": round(self._score_entry(e), 3),
                    "last_used": e.get("last_used"),
                }
        return report

    def recommend_routing(self, task_type: str) -> list[str]:
        """Models that have handled task_type, sorted best score first."""
        seen = [(m, self.get_task_score(m, task_type))
                for m, tasks in self._data.items() if task_type in tasks]
        seen.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in seen]

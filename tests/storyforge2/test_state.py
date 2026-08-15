"""
tests/storyforge2/test_state.py — SQLite stage ledger.

Verifies the properties the pipeline actually depends on: append-only stage
history, resumability, and approval gating.
"""

import pytest

from storyforge2.state import (
    APPROVAL_GATES, STAGE_STATUSES, STAGES, StateError, StateStore,
)


@pytest.fixture
def store(tmp_path):
    return StateStore(db_path=str(tmp_path / "state.db"))


@pytest.fixture
def project(store):
    return store.create_project({"title": "Test Book", "author": "Tester"})


def test_stages_are_in_pipeline_order():
    assert STAGES[0] == "brief"
    assert STAGES[-1] == "results"
    assert STAGES.index("manuscript") < STAGES.index("layout") < STAGES.index("cover")
    assert STAGES.index("export") < STAGES.index("publish")
    assert len(set(STAGES)) == len(STAGES)


def test_approval_gates_precede_publish():
    assert "publish" in APPROVAL_GATES
    assert "manuscript" in APPROVAL_GATES


def test_create_and_get_project(store):
    brief = {"title": "Dragons", "author": "J. Jardin", "chapters": 12}
    pid = store.create_project(brief)
    fetched = store.get_project(pid)
    assert fetched is not None
    assert fetched.brief == brief
    assert fetched.status == "active"


def test_get_missing_project_returns_none(store):
    assert store.get_project("does-not-exist") is None


def test_start_stage_rejects_unknown_stage(store, project):
    with pytest.raises(StateError):
        store.start_stage(project, "not_a_real_stage")


def test_stage_lifecycle_running_to_completed(store, project):
    run = store.start_stage(project, "manuscript", inputs={"words": 30000})
    assert run.status == "running"
    assert run.attempt_number == 1
    assert store.is_stage_complete(project, "manuscript") is False

    store.complete_stage(run.id, {"path": "book.md"})
    assert store.is_stage_complete(project, "manuscript") is True
    assert store.latest_stage_run(project, "manuscript").outputs == {"path": "book.md"}


def test_failed_stage_is_not_complete(store, project):
    run = store.start_stage(project, "cover")
    store.fail_stage(run.id, "image provider timed out")
    latest = store.latest_stage_run(project, "cover")
    assert latest.status == "failed"
    assert latest.error == "image provider timed out"
    assert store.is_stage_complete(project, "cover") is False


def test_skipped_stage_is_not_complete(store, project):
    run = store.start_stage(project, "illustrations")
    store.skip_stage(run.id, "text-only book")
    assert store.latest_stage_run(project, "illustrations").status == "skipped"
    assert store.is_stage_complete(project, "illustrations") is False


def test_retry_appends_history_without_overwriting(store, project):
    """The core resumability guarantee: a retry must not destroy the prior attempt."""
    first = store.start_stage(project, "cover")
    store.fail_stage(first.id, "provider 500")

    second = store.start_stage(project, "cover")
    assert second.attempt_number == 2
    store.complete_stage(second.id, {"path": "cover.png"})

    assert store.is_stage_complete(project, "cover") is True
    history = [r for r in store.all_stage_runs(project) if r.stage_name == "cover"]
    assert len(history) == 2
    assert history[0].status == "failed"
    assert history[0].error == "provider 500"


def test_latest_stage_run_returns_highest_attempt(store, project):
    for _ in range(3):
        store.start_stage(project, "export")
    assert store.latest_stage_run(project, "export").attempt_number == 3


def test_latest_stage_runs_one_entry_per_stage(store, project):
    store.complete_stage(store.start_stage(project, "brief").id, {})
    store.start_stage(project, "manuscript")
    store.start_stage(project, "manuscript")

    latest = store.latest_stage_runs(project)
    assert set(latest) == {"brief", "manuscript"}
    assert latest["manuscript"].attempt_number == 2


def test_projects_are_isolated(store):
    a = store.create_project({"title": "A"})
    b = store.create_project({"title": "B"})
    store.complete_stage(store.start_stage(a, "manuscript").id, {})

    assert store.is_stage_complete(a, "manuscript") is True
    assert store.is_stage_complete(b, "manuscript") is False
    assert store.all_stage_runs(b) == []


def test_stage_statuses_used_are_declared(store, project):
    """Every status the store writes must be in the declared vocabulary."""
    store.complete_stage(store.start_stage(project, "brief").id, {})
    store.fail_stage(store.start_stage(project, "outline").id, "err")
    store.skip_stage(store.start_stage(project, "illustrations").id, "n/a")
    running = store.start_stage(project, "layout")

    for run in store.all_stage_runs(project):
        assert run.status in STAGE_STATUSES
    assert running.status in STAGE_STATUSES


def test_approval_gate_defaults_to_unapproved(store, project):
    assert store.is_approved(project, "publish") is False


def test_approve_and_revoke(store, project):
    store.approve(project, "publish", approved_by="josh")
    assert store.is_approved(project, "publish") is True
    store.revoke_approval(project, "publish")
    assert store.is_approved(project, "publish") is False


def test_approve_rejects_unknown_gate(store, project):
    with pytest.raises(StateError):
        store.approve(project, "not_a_gate")


def test_approval_is_per_project(store):
    a = store.create_project({"title": "A"})
    b = store.create_project({"title": "B"})
    store.approve(a, "publish")
    assert store.is_approved(a, "publish") is True
    assert store.is_approved(b, "publish") is False


def test_state_survives_reopen(tmp_path):
    """Resumability across process restarts — the whole point of the ledger."""
    db = str(tmp_path / "state.db")
    store = StateStore(db_path=db)
    pid = store.create_project({"title": "Persisted"})
    store.complete_stage(store.start_stage(pid, "manuscript").id, {"path": "b.md"})
    store.approve(pid, "manuscript")

    reopened = StateStore(db_path=db)
    assert reopened.get_project(pid).brief["title"] == "Persisted"
    assert reopened.is_stage_complete(pid, "manuscript") is True
    assert reopened.is_approved(pid, "manuscript") is True

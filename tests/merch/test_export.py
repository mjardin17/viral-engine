"""
tests/merch/test_export.py -- MerchPulse export ingest.

The property that matters most: demo-seeded records can never be mistaken
for real product. Everything in the shipped export except the trend signals
is demo data, so a publish path that ignores `is_demo` would push a fake
t-shirt to a live store.
"""

import json

import pytest

from merch.export_ingest import (
    CampaignChain, MerchExportError, MerchPulseExport, load_export,
)


def _export(**entities):
    """Build a minimal export, defaulting absent entities to empty lists."""
    return MerchPulseExport({k: v for k, v in entities.items()})


def _rec(record_id, **fields):
    return {"id": record_id, **fields}


# -- structural validation -------------------------------------------------

def test_top_level_must_be_an_object():
    with pytest.raises(MerchExportError):
        MerchPulseExport([])  # type: ignore[arg-type]


def test_entity_must_map_to_a_list():
    with pytest.raises(MerchExportError):
        MerchPulseExport({"Product": {"id": "p1"}})  # type: ignore[dict-item]


def test_record_without_id_is_rejected():
    with pytest.raises(MerchExportError, match="has no id"):
        MerchPulseExport({"Product": [{"retail_price": 24.99}]})


def test_duplicate_ids_are_rejected():
    with pytest.raises(MerchExportError, match="duplicate id"):
        MerchPulseExport({"Product": [_rec("p1"), _rec("p1")]})


def test_dangling_foreign_key_is_rejected():
    """An orphan listing is how a product ships with no design attached."""
    with pytest.raises(MerchExportError, match="does not exist"):
        _export(Listing=[_rec("l1", product_id="p_missing")])


def test_null_foreign_key_is_allowed():
    """Null means 'not linked yet', which the schema permits -- a Concept
    exists before its Campaign does."""
    exp = _export(Concept=[_rec("c1", opportunity_id=None, campaign_id=None)])
    assert len(exp.records("Concept")) == 1


def test_resolvable_foreign_key_passes():
    exp = _export(
        Product=[_rec("p1")],
        Listing=[_rec("l1", product_id="p1")],
    )
    assert exp.get("Product", "p1") is not None


def test_load_export_rejects_missing_file(tmp_path):
    with pytest.raises(MerchExportError, match="not a file"):
        load_export(tmp_path / "nope.json")


def test_load_export_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(MerchExportError, match="invalid JSON"):
        load_export(bad)


def test_load_export_round_trips(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(json.dumps({"Product": [_rec("p1")]}), encoding="utf-8")
    assert load_export(path).counts() == {"Product": 1}


def test_unknown_entities_are_reported_not_rejected():
    """A new entity from the app is not an error, but ignoring it silently is."""
    exp = _export(Product=[_rec("p1")], Sponsorship=[_rec("s1")])
    assert exp.unknown_entities() == ["Sponsorship"]


# -- demo quarantine -------------------------------------------------------

def test_chain_is_demo_if_any_part_is_demo():
    """Pessimistic by design: a real campaign on a demo design still puts
    demo artwork on a live product."""
    chain = CampaignChain(
        campaign=_rec("c1", is_demo=False),
        design=_rec("d1", is_demo=True),
    )
    assert chain.is_demo is True


def test_chain_is_real_only_when_every_part_is_real():
    chain = CampaignChain(
        campaign=_rec("c1", is_demo=False),
        design=_rec("d1", is_demo=False),
    )
    assert chain.is_demo is False


def test_demo_campaign_is_not_publishable():
    chain = CampaignChain(campaign=_rec("c1", is_demo=True, approved=True))
    ok, reason = chain.is_publishable()
    assert ok is False
    assert "demo" in reason


def test_real_campaigns_excludes_demo():
    exp = _export(Campaign=[
        _rec("c1", name="demo", is_demo=True),
        _rec("c2", name="real", is_demo=False),
    ])
    assert [c.name for c in exp.real_campaigns()] == ["real"]
    assert [c.name for c in exp.demo_campaigns()] == ["demo"]


# -- publishability gate ---------------------------------------------------

def _full_chain(**overrides):
    base = dict(
        campaign=_rec("c1", approved=True, is_demo=False),
        concept=_rec("k1", is_demo=False, ip_vetoed=False),
        design=_rec("d1", is_demo=False, print_quality_ok=True),
        product=_rec("p1", is_demo=False),
        listing=_rec("l1", is_demo=False),
    )
    base.update(overrides)
    return CampaignChain(**base)


def test_complete_approved_chain_is_publishable():
    ok, reason = _full_chain().is_publishable()
    assert ok is True, reason


def test_incomplete_chain_names_what_is_missing():
    chain = _full_chain(design=None, listing=None)
    ok, reason = chain.is_publishable()
    assert ok is False
    assert "design" in reason and "listing" in reason
    assert chain.missing_parts == ["design", "listing"]


def test_unapproved_campaign_is_not_publishable():
    ok, reason = _full_chain(campaign=_rec("c1", approved=False)).is_publishable()
    assert ok is False
    assert "not approved" in reason


def test_design_failing_print_quality_is_not_publishable():
    chain = _full_chain(design=_rec("d1", print_quality_ok=False))
    ok, reason = chain.is_publishable()
    assert ok is False
    assert "print-quality" in reason


def test_ip_vetoed_concept_is_not_publishable():
    """IP veto is the one gate whose failure is legally expensive."""
    chain = _full_chain(concept=_rec("k1", ip_vetoed=True))
    ok, reason = chain.is_publishable()
    assert ok is False
    assert "IP" in reason


# -- findings --------------------------------------------------------------

def _severities(exp, entity):
    return [f.severity for f in exp.findings() if f.entity == entity]


def test_all_demo_campaigns_raises_a_blocker():
    exp = _export(Campaign=[_rec("c1", is_demo=True)])
    assert "blocker" in _severities(exp, "Campaign")


def test_partially_demo_campaigns_warn_rather_than_block():
    exp = _export(Campaign=[
        _rec("c1", is_demo=True),
        _rec("c2", is_demo=False),
    ])
    assert _severities(exp, "Campaign") == ["warn"]


def test_web_search_trend_without_source_url_is_flagged():
    """An unverifiable citation is worse than none -- it reads as evidence."""
    exp = _export(TrendSignal=[
        _rec("t1", phrase="Spooky Beans", is_demo=False,
             source="web_search", source_url=""),
    ])
    messages = [f.message for f in exp.findings() if f.entity == "TrendSignal"]
    assert any("source_url" in m for m in messages)


def test_trend_with_a_source_url_is_not_flagged_for_citation():
    exp = _export(TrendSignal=[
        _rec("t1", phrase="Cited", is_demo=False,
             source="web_search", source_url="https://example.com/report"),
    ])
    messages = [f.message for f in exp.findings() if f.entity == "TrendSignal"]
    assert not any("source_url" in m for m in messages)


def test_trend_never_acted_on_is_surfaced():
    exp = _export(TrendSignal=[_rec("t1", phrase="Stranded", is_demo=False)])
    messages = [f.message for f in exp.findings() if f.entity == "TrendSignal"]
    assert any("no Opportunity" in m for m in messages)


def test_trend_with_an_opportunity_is_not_called_stranded():
    exp = _export(
        TrendSignal=[_rec("t1", phrase="Acted on", is_demo=False)],
        Opportunity=[_rec("o1", trend_id="t1")],
    )
    messages = [f.message for f in exp.findings() if f.entity == "TrendSignal"]
    assert not any("no Opportunity" in m for m in messages)


def test_dry_run_only_publish_jobs_are_reported_as_not_live():
    exp = _export(
        Campaign=[_rec("c1", is_demo=True)],
        PublishJob=[_rec("j1", campaign_id="c1", mode="dry_run", status="dry_run")],
    )
    messages = [f.message for f in exp.findings() if f.entity == "PublishJob"]
    assert any("none live" in m for m in messages)


def test_live_job_on_a_disconnected_channel_is_a_blocker():
    """Claiming a live listing on a channel that was never connected means
    either the status or the connection flag is lying."""
    exp = _export(
        Channel=[_rec("ch1", name="Etsy", connected=False)],
        PublishJob=[_rec("j1", channel_id="ch1", channel_name="Etsy",
                         status="published", mode="live")],
    )
    blockers = [f for f in exp.findings()
                if f.entity == "PublishJob" and f.severity == "blocker"]
    assert len(blockers) == 1


def test_live_job_on_a_connected_channel_is_clean():
    exp = _export(
        Channel=[_rec("ch1", name="Etsy", connected=True)],
        PublishJob=[_rec("j1", channel_id="ch1", channel_name="Etsy",
                         status="published", mode="live")],
    )
    assert not [f for f in exp.findings() if f.severity == "blocker"]


def test_findings_are_ordered_blocker_first():
    exp = _export(
        Campaign=[_rec("c1", is_demo=True)],
        TrendSignal=[_rec("t1", phrase="x", is_demo=False,
                          source="web_search", source_url="")],
    )
    severities = [f.severity for f in exp.findings()]
    assert severities == sorted(severities, key={"blocker": 0, "warn": 1, "info": 2}.get)

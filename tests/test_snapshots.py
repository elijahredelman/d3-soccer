import json

from d3soccer.pipelines import snapshots


def touch(d, name, data=None):
    (d / name).write_text(json.dumps(data or {}))
    return d / name


def test_latest_per_family_orders_by_date_then_family(snapshot_dir):
    touch(snapshot_dir, "sciac_snapshot_2026-09-18.json")
    sciac = touch(snapshot_dir, "sciac_snapshot_2026-10-06.json")
    conf3 = touch(snapshot_dir, "conferences3_snapshot_2026-10-06.json")
    conf = touch(snapshot_dir, "conferences_snapshot_2026-10-07.json")
    touch(snapshot_dir, "leaders_snapshot_2026-10-08.json")

    # Same date: the order CONFERENCE_FAMILIES lists them, so newer data merges last.
    assert snapshots.latest_per_family(snapshots.CONFERENCE_FAMILIES) == [sciac, conf3, conf]


def test_write_is_compact_and_prune_keeps_only_new_file(snapshot_dir):
    old = touch(snapshot_dir, "conferences3_snapshot_2026-10-06.json")
    other = touch(snapshot_dir, "leaders_snapshot_2026-10-06.json")
    new = snapshots.write("conferences", {"a": [1, 2]})

    assert new.read_text() == '{"a":[1,2]}'
    assert snapshots.prune(snapshots.CONFERENCE_FAMILIES, keep=new) == [old]
    assert new.exists() and other.exists() and not old.exists()


def test_report_writes_github_summary(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    snapshots.report("National", ["NPI rankings: empty result"])
    assert "1 failed fetches" in summary.read_text()
    assert "- NPI rankings: empty result" in summary.read_text()

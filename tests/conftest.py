import pytest

from d3soccer.pipelines import snapshots


@pytest.fixture
def snapshot_dir(tmp_path, monkeypatch):
    """Point every snapshot read/write at an empty temp directory."""
    monkeypatch.setattr(snapshots, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return tmp_path

import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
from source import constants
import pyarrow.parquet as pq
from unittest.mock import patch
from source.query import _resolve_parquet_root, run_query


# build a tiny tags partition under root so duckdb has something to view
def _make_tags_partition(root: Path) -> None:
    d = root / "tags" / "year_month=all"
    d.mkdir(parents=True)
    table = pa.table(
        {"Id": [1, 2, 3], "TagName": ["py", "js", "go"], "Count": [100, 50, 25]}
    )
    pq.write_table(table, d / "data.parquet")


# repoint constants and reset the singleton connection per test
@pytest.fixture
def fake_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _make_tags_partition(tmp_path)
    monkeypatch.setattr(constants, "PROCESSED", tmp_path)
    import source.query as q

    monkeypatch.setattr(q, "_conn", None)
    return tmp_path


def test_resolve_parquet_root_uses_processed(fake_parquet: Path) -> None:
    assert _resolve_parquet_root() == fake_parquet


def test_resolve_parquet_root_raises_when_neither_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(constants, "PROCESSED", None)
    with patch("source.query.snapshot_download", side_effect=Exception("not cached")):
        with pytest.raises(RuntimeError, match=r"(?i)no parquet"):
            _resolve_parquet_root()


def test_run_query_returns_dataframe(fake_parquet: Path) -> None:
    df = run_query("SELECT * FROM tags ORDER BY Id")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert list(df["TagName"]) == ["py", "js", "go"]


def test_run_query_with_positional_params(fake_parquet: Path) -> None:
    df = run_query("SELECT * FROM tags WHERE Count >= ?", params=[50])
    assert len(df) == 2
    assert set(df["TagName"]) == {"py", "js"}


def test_run_query_guardrail_aborts_when_too_many_rows(fake_parquet: Path) -> None:
    with pytest.raises(RuntimeError, match=r"(?i)would return"):
        run_query("SELECT * FROM tags", max_rows=2)

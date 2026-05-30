import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime, timedelta

from source import constants
from source.metrics.acceptance import (
    monthly_time_to_acceptance,
    write_acceptance_report,
)


# build a tiny posts partition with accepted-answer references
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    q1 = datetime(2024, 1, 5, 12, 0, 0)
    q2 = datetime(2024, 1, 10, 12, 0, 0)
    q3 = datetime(2024, 2, 1, 12, 0, 0)
    table = pa.table(
        {
            "Id": [1, 2, 3, 11, 12, 13],
            "PostTypeId": [1, 1, 1, 2, 2, 2],
            "ParentId": [None, None, None, 1, 2, 3],
            "AcceptedAnswerId": [11, 12, None, None, None, None],
            "CreationDate": [
                q1,
                q2,
                q3,
                q1 + timedelta(seconds=200),
                q2 + timedelta(seconds=400),
                q3 + timedelta(seconds=600),
            ],
        }
    )
    pq.write_table(table, d / "data.parquet")


# minimal stub partition for the other tables (silences view-creation warnings)
def _make_stub(root: Path, name: str) -> None:
    d = root / name / "year_month=2024-01"
    d.mkdir(parents=True)
    pq.write_table(pa.table({"Id": [1]}), d / "data.parquet")


# repoint constants and reset the singleton connection per test
@pytest.fixture
def fake_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _make_posts(tmp_path)
    for t in ("users", "comments", "postlinks", "tags"):
        _make_stub(tmp_path, t)
    monkeypatch.setattr(constants, "PROCESSED", tmp_path)
    monkeypatch.setattr(constants, "START", date(2024, 1, 1))
    import source.query as q

    monkeypatch.setattr(q, "_conn", None)
    return tmp_path


# verify the median uses the accepted answer's creation date
def test_monthly_time_to_acceptance_computes_median(fake_parquet: Path) -> None:
    df = monthly_time_to_acceptance(start=date(2024, 1, 1))
    # Only Jan has accepted answers (Q3 has no acceptance, so Feb yields no row)
    assert len(df) == 1
    jan = df.iloc[0]
    assert jan["year_month"] == "2024-01"
    assert int(jan["accepted_count"]) == 2
    # median of [200, 400] = 300
    assert jan["median_seconds"] == pytest.approx(300.0)


# verify the report writer creates a csv with the expected columns
def test_write_acceptance_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_acceptance_report()
    written = out / "time_to_acceptance.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {
        "year_month",
        "accepted_count",
        "median_seconds",
        "p90_seconds",
    }.issubset(df.columns)

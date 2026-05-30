import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime

from source import constants
from source.metrics.askers import monthly_active_askers, write_askers_report


# build a tiny posts partition with repeat askers and one anonymous question
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5, 6],
            "PostTypeId": [1, 1, 1, 1, 1, 2],
            "OwnerUserId": [10, 10, 20, None, 30, 40],
            "CreationDate": [
                datetime(2024, 1, 5),
                datetime(2024, 1, 6),
                datetime(2024, 1, 15),
                datetime(2024, 1, 20),
                datetime(2024, 2, 2),
                datetime(2024, 2, 3),
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


# verify distinct askers counts non-null owner ids and excludes answers
def test_monthly_active_askers_counts_distinct_non_null(fake_parquet: Path) -> None:
    df = monthly_active_askers(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    # Jan questions: askers 10 (twice), 20, NULL -> distinct non-null = 2
    assert int(jan["distinct_askers"]) == 2
    # Feb questions: asker 30 -> 1. (Id 6 is an answer, excluded by PostTypeId filter)
    assert int(feb["distinct_askers"]) == 1


# verify the report writer creates a csv with the expected columns
def test_write_askers_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_askers_report()
    written = out / "active_askers.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "distinct_askers"}.issubset(df.columns)

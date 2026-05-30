import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime, timedelta

from source import constants
from source.metrics.response import monthly_time_to_first_answer, write_response_report


# build a tiny posts partition with questions and matching answers
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    q1 = datetime(2024, 1, 5, 12, 0, 0)
    q2 = datetime(2024, 1, 10, 12, 0, 0)
    q3 = datetime(2024, 2, 1, 12, 0, 0)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5, 6, 7],
            "PostTypeId": [1, 1, 1, 2, 2, 2, 2],
            "ParentId": [None, None, None, 1, 1, 2, 3],
            "CreationDate": [
                q1,
                q2,
                q3,
                q1 + timedelta(seconds=60),
                q1 + timedelta(seconds=300),
                q2 + timedelta(seconds=120),
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


# verify median and p90 use the earliest answer per question
def test_monthly_time_to_first_answer_uses_earliest(fake_parquet: Path) -> None:
    df = monthly_time_to_first_answer(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    # Jan: Q1 first answer at +60s, Q2 first answer at +120s -> 2 questions answered
    assert int(jan["answered_count"]) == 2
    # median of [60, 120] = 90
    assert jan["median_seconds"] == pytest.approx(90.0)
    # Feb: Q3 first answer at +600s -> 1 question, median = 600
    assert int(feb["answered_count"]) == 1
    assert feb["median_seconds"] == pytest.approx(600.0)


# verify the report writer creates a csv with the expected columns
def test_write_response_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_response_report()
    written = out / "time_to_first_answer.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "answered_count", "median_seconds", "p90_seconds"}.issubset(
        df.columns
    )

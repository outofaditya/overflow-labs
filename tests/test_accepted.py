import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import date, datetime

from source import constants
from source.metrics import monthly_accepted_rate, write_accepted_report


# build a tiny posts partition with mixed accepted and non-accepted questions
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5, 6, 7],
            "PostTypeId": [1, 1, 1, 1, 1, 1, 2],
            "AcceptedAnswerId": [101, 102, None, 103, None, None, None],
            "CreationDate": [
                datetime(2024, 1, 5),
                datetime(2024, 1, 10),
                datetime(2024, 1, 15),
                datetime(2024, 1, 20),
                datetime(2024, 2, 1),
                datetime(2024, 2, 5),
                datetime(2024, 2, 6),
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


# verify the accepted-rate per month matches expected fractions
def test_monthly_accepted_rate_computes_fraction(fake_parquet: Path) -> None:
    df = monthly_accepted_rate(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    # Jan: 4 questions, 3 accepted -> 0.75
    assert int(jan["question_count"]) == 4
    assert jan["accepted_rate"] == pytest.approx(0.75)
    # Feb: 2 questions (Id 7 is an answer), 0 accepted -> 0.0
    assert int(feb["question_count"]) == 2
    assert feb["accepted_rate"] == pytest.approx(0.0)


# verify the report writer creates a csv with the expected columns
def test_write_accepted_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_accepted_report()
    written = out / "accepted_rate.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "question_count", "accepted_rate"}.issubset(df.columns)

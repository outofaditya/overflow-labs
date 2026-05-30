import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime

from source import constants
from source.metrics.volume import monthly_volume, write_volume_report


# build a tiny posts partition with a mix of questions and answers
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5],
            "PostTypeId": [1, 1, 2, 1, 2],
            "CreationDate": [
                datetime(2024, 1, 5),
                datetime(2024, 1, 15),
                datetime(2024, 1, 16),
                datetime(2024, 2, 1),
                datetime(2024, 2, 2),
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


# verify the monthly volume counts questions and answers per month
def test_monthly_volume_returns_expected_counts(fake_parquet: Path) -> None:
    df = monthly_volume(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["question_count"]) == 2
    assert int(jan["answer_count"]) == 1
    assert int(feb["question_count"]) == 1
    assert int(feb["answer_count"]) == 1


# verify the report writer creates a csv with the expected columns
def test_write_volume_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_volume_report()
    written = out / "monthly_volume.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "question_count", "answer_count"}.issubset(df.columns)

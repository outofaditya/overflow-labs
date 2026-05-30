import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime

from source import constants
from source.metrics import monthly_answer_coverage, write_coverage_report


# build a tiny posts partition with mixed answered and unanswered questions
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5, 6, 7],
            "PostTypeId": [1, 1, 1, 1, 1, 1, 2],
            "AnswerCount": [2, 0, 1, None, 3, 0, None],
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


# verify the coverage rate counts answered fraction and treats null as zero
def test_monthly_answer_coverage_computes_fraction(fake_parquet: Path) -> None:
    df = monthly_answer_coverage(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    # Jan: 4 questions, answered (AnswerCount > 0) = Id 1 and Id 3 -> 2/4 = 0.5
    assert int(jan["question_count"]) == 4
    assert jan["coverage_rate"] == pytest.approx(0.5)
    # Feb: 2 questions (Id 7 is an answer), answered = Id 5 only -> 1/2 = 0.5
    assert int(feb["question_count"]) == 2
    assert feb["coverage_rate"] == pytest.approx(0.5)


# verify the report writer creates a csv with the expected columns
def test_write_coverage_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_coverage_report()
    written = out / "answer_coverage.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "question_count", "coverage_rate"}.issubset(df.columns)

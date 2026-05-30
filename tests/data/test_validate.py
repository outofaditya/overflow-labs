import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
import pyarrow.parquet as pq
from datetime import date, datetime

from source import constants
from source.data.validate import (
    summarize_table,
    questions_per_month,
    write_validation_report,
)


# build a tiny posts partition with the given creation dates
def _make_posts(root: Path, dates: list[datetime]) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": list(range(1, len(dates) + 1)),
            "PostTypeId": [1] * len(dates),
            "CreationDate": dates,
        }
    )
    pq.write_table(table, d / "data.parquet")


# build a tiny tags partition (unpartitioned table uses year_month=all)
def _make_tags(root: Path) -> None:
    d = root / "tags" / "year_month=all"
    d.mkdir(parents=True)
    pq.write_table(
        pa.table({"Id": [1, 2], "TagName": ["py", "js"], "Count": [100, 50]}),
        d / "data.parquet",
    )


# build a stub partition for a date-bearing table we are not focused on
def _make_stub(root: Path, name: str) -> None:
    d = root / name / "year_month=2024-01"
    d.mkdir(parents=True)
    pq.write_table(
        pa.table({"Id": [1], "CreationDate": [datetime(2024, 1, 1)]}),
        d / "data.parquet",
    )


# repoint constants and reset the singleton connection per test
@pytest.fixture
def fake_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _make_posts(
        tmp_path,
        [
            datetime(2024, 1, 15),
            datetime(2024, 1, 20),
            datetime(2024, 2, 5),
        ],
    )
    _make_tags(tmp_path)
    for t in ("users", "comments", "postlinks"):
        _make_stub(tmp_path, t)
    monkeypatch.setattr(constants, "PROCESSED", tmp_path)
    monkeypatch.setattr(constants, "START", date(2024, 1, 1))
    import source.data.query as q

    monkeypatch.setattr(q, "_conn", None)
    return tmp_path


# verify summary returns row count, partitions, and date bounds when requested
def test_summarize_table_with_dates(fake_parquet: Path) -> None:
    summary = summarize_table("posts", has_dates=True)
    assert summary["table"] == "posts"
    assert summary["row_count"] == 3
    assert summary["partitions"] == 1
    assert summary["first_date"] is not None
    assert summary["last_date"] is not None


# verify the unpartitioned table summary skips date bounds
def test_summarize_table_skips_dates_when_flag_false(fake_parquet: Path) -> None:
    summary = summarize_table("tags", has_dates=False)
    assert summary["row_count"] == 2
    assert summary["first_date"] is None
    assert summary["last_date"] is None


# verify the monthly series returns one row per observed month
def test_questions_per_month_returns_full_window(fake_parquet: Path) -> None:
    monthly = questions_per_month(start=date(2024, 1, 1))
    assert len(monthly) == 2
    assert monthly["question_count"].tolist() == [2, 1]
    assert monthly["is_gap"].tolist() == [False, False]


# verify gap detection for months with no data inside the window
def test_questions_per_month_detects_missing_months(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_posts(tmp_path, [datetime(2024, 1, 1), datetime(2024, 5, 1)])
    _make_tags(tmp_path)
    for t in ("users", "comments", "postlinks"):
        _make_stub(tmp_path, t)
    monkeypatch.setattr(constants, "PROCESSED", tmp_path)
    monkeypatch.setattr(constants, "START", date(2024, 1, 1))
    import source.data.query as q

    monkeypatch.setattr(q, "_conn", None)

    monthly = questions_per_month(start=date(2024, 1, 1))
    assert len(monthly) == 5
    assert int(monthly["is_gap"].sum()) == 3


# verify the full validation report writes both csvs with all 5 tables listed
def test_write_validation_report_creates_both_csvs(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_validation_report()
    assert (out / "data_validation.csv").is_file()
    assert (out / "posts_per_month.csv").is_file()
    summary = pd.read_csv(out / "data_validation.csv")
    assert set(summary["table"]) == {"posts", "users", "comments", "postlinks", "tags"}

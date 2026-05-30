import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import date, datetime

from source import constants
from source.metrics import monthly_engagement, write_engagement_report


# build a tiny posts partition with varying scores and comment counts
def _make_posts(root: Path) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    table = pa.table(
        {
            "Id": [1, 2, 3, 4, 5, 6],
            "PostTypeId": [1, 1, 1, 1, 1, 2],
            "Score": [10, 6, 2, 4, 8, 99],
            "CommentCount": [2, 0, None, 3, 1, 50],
            "CreationDate": [
                datetime(2024, 1, 5),
                datetime(2024, 1, 10),
                datetime(2024, 1, 15),
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


# verify mean score and mean comments are computed per month and exclude answers
def test_monthly_engagement_computes_means(fake_parquet: Path) -> None:
    df = monthly_engagement(start=date(2024, 1, 1))
    assert len(df) == 2
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    # Jan questions: scores [10, 6, 2] -> mean 6.0; comments [2, 0, 0 from null] -> mean ~0.667
    assert int(jan["question_count"]) == 3
    assert jan["mean_score"] == pytest.approx(6.0)
    assert jan["mean_comments"] == pytest.approx(2 / 3)
    # Feb questions: scores [4, 8] -> mean 6.0; comments [3, 1] -> mean 2.0
    assert int(feb["question_count"]) == 2
    assert feb["mean_score"] == pytest.approx(6.0)
    assert feb["mean_comments"] == pytest.approx(2.0)


# verify the report writer creates a csv with the expected columns
def test_write_engagement_report_creates_csv(
    fake_parquet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out)
    write_engagement_report()
    written = out / "engagement.csv"
    assert written.is_file()
    df = pd.read_csv(written)
    assert {"year_month", "question_count", "mean_score", "mean_comments"}.issubset(
        df.columns
    )

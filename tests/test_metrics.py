import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import date, datetime, timedelta

from source import constants
from source.metrics import (
    monthly_accepted_rate,
    monthly_active_askers,
    monthly_answer_coverage,
    monthly_engagement,
    monthly_time_to_acceptance,
    monthly_time_to_first_answer,
    monthly_volume,
    write_accepted_report,
    write_acceptance_report,
    write_askers_report,
    write_coverage_report,
    write_engagement_report,
    write_response_report,
    write_volume_report,
)


# write a posts parquet partition under root from a dict of column to values
def _write_posts(root: Path, columns: dict) -> None:
    d = root / "posts" / "year_month=2024-01"
    d.mkdir(parents=True)
    pq.write_table(pa.table(columns), d / "data.parquet")


# write minimal stubs for the non-posts tables to silence view-creation warnings
def _write_stubs(root: Path) -> None:
    for name in ("users", "comments", "postlinks", "tags"):
        d = root / name / "year_month=2024-01"
        d.mkdir(parents=True)
        pq.write_table(pa.table({"Id": [1]}), d / "data.parquet")


# repoint constants and reset the singleton query connection per test
@pytest.fixture
def parquet_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _write_stubs(tmp_path)
    monkeypatch.setattr(constants, "PROCESSED", tmp_path)
    monkeypatch.setattr(constants, "START", date(2024, 1, 1))
    import source.query as q

    monkeypatch.setattr(q, "_conn", None)
    return tmp_path


# universal posts shape with every column any metric query references
_Q = datetime(2024, 1, 5, 12, 0, 0)
_UNIVERSAL_POSTS = {
    "Id": [1, 11],
    "PostTypeId": [1, 2],
    "ParentId": [None, 1],
    "OwnerUserId": [10, 20],
    "AcceptedAnswerId": [11, None],
    "AnswerCount": [1, None],
    "Score": [5, 3],
    "CommentCount": [1, 0],
    "CreationDate": [_Q, _Q + timedelta(seconds=60)],
}


# verify the monthly volume counts questions and answers per month
def test_monthly_volume_counts_questions_and_answers(parquet_root: Path) -> None:
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_volume(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["question_count"]) == 2
    assert int(jan["answer_count"]) == 1
    assert int(feb["question_count"]) == 1
    assert int(feb["answer_count"]) == 1


# verify distinct askers counts non-null owner ids and excludes answers
def test_monthly_active_askers_counts_distinct_non_null(parquet_root: Path) -> None:
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_active_askers(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["distinct_askers"]) == 2
    assert int(feb["distinct_askers"]) == 1


# verify the accepted-rate per month matches expected fractions
def test_monthly_accepted_rate_computes_fraction(parquet_root: Path) -> None:
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_accepted_rate(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["question_count"]) == 4
    assert jan["accepted_rate"] == pytest.approx(0.75)
    assert int(feb["question_count"]) == 2
    assert feb["accepted_rate"] == pytest.approx(0.0)


# verify the coverage rate counts answered fraction and treats null as zero
def test_monthly_answer_coverage_computes_fraction(parquet_root: Path) -> None:
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_answer_coverage(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["question_count"]) == 4
    assert jan["coverage_rate"] == pytest.approx(0.5)
    assert int(feb["question_count"]) == 2
    assert feb["coverage_rate"] == pytest.approx(0.5)


# verify the time-to-first-answer median uses the earliest answer per question
def test_monthly_time_to_first_answer_uses_earliest(parquet_root: Path) -> None:
    q1 = datetime(2024, 1, 5, 12, 0, 0)
    q2 = datetime(2024, 1, 10, 12, 0, 0)
    q3 = datetime(2024, 2, 1, 12, 0, 0)
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_time_to_first_answer(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["answered_count"]) == 2
    assert jan["median_seconds"] == pytest.approx(90.0)
    assert int(feb["answered_count"]) == 1
    assert feb["median_seconds"] == pytest.approx(600.0)


# verify the time-to-acceptance median uses the accepted answer's creation date
def test_monthly_time_to_acceptance_computes_median(parquet_root: Path) -> None:
    q1 = datetime(2024, 1, 5, 12, 0, 0)
    q2 = datetime(2024, 1, 10, 12, 0, 0)
    q3 = datetime(2024, 2, 1, 12, 0, 0)
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_time_to_acceptance(start=date(2024, 1, 1))
    assert len(df) == 1
    jan = df.iloc[0]
    assert jan["year_month"] == "2024-01"
    assert int(jan["accepted_count"]) == 2
    assert jan["median_seconds"] == pytest.approx(300.0)


# verify mean score and mean comments are computed per month and exclude answers
def test_monthly_engagement_computes_means(parquet_root: Path) -> None:
    _write_posts(
        parquet_root,
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
        },
    )
    df = monthly_engagement(start=date(2024, 1, 1))
    jan = df[df["year_month"] == "2024-01"].iloc[0]
    feb = df[df["year_month"] == "2024-02"].iloc[0]
    assert int(jan["question_count"]) == 3
    assert jan["mean_score"] == pytest.approx(6.0)
    assert jan["mean_comments"] == pytest.approx(2 / 3)
    assert int(feb["question_count"]) == 2
    assert feb["mean_score"] == pytest.approx(6.0)
    assert feb["mean_comments"] == pytest.approx(2.0)


# parametrized writer test: every report function lands a csv with expected columns
_WRITER_CASES = [
    (
        write_volume_report,
        "monthly_volume.csv",
        {"year_month", "question_count", "answer_count"},
    ),
    (
        write_askers_report,
        "active_askers.csv",
        {"year_month", "distinct_askers"},
    ),
    (
        write_accepted_report,
        "accepted_rate.csv",
        {"year_month", "question_count", "accepted_rate"},
    ),
    (
        write_coverage_report,
        "answer_coverage.csv",
        {"year_month", "question_count", "coverage_rate"},
    ),
    (
        write_response_report,
        "time_to_first_answer.csv",
        {"year_month", "answered_count", "median_seconds", "p90_seconds"},
    ),
    (
        write_acceptance_report,
        "time_to_acceptance.csv",
        {"year_month", "accepted_count", "median_seconds", "p90_seconds"},
    ),
    (
        write_engagement_report,
        "engagement.csv",
        {"year_month", "question_count", "mean_score", "mean_comments"},
    ),
]


@pytest.mark.parametrize("writer, filename, expected_columns", _WRITER_CASES)
def test_writer_creates_csv_with_expected_columns(
    parquet_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
    filename: str,
    expected_columns: set[str],
) -> None:
    _write_posts(parquet_root, _UNIVERSAL_POSTS)
    out_dir = parquet_root / "results_tables"
    monkeypatch.setattr(constants, "TABLES", out_dir)
    writer()
    written = out_dir / filename
    assert written.is_file()
    df = pd.read_csv(written)
    assert expected_columns.issubset(df.columns)

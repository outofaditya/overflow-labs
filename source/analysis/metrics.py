from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.logger import get_logger
from source.data.query import run_query

# initialize logger
log = get_logger(__name__)


# write a metric dataframe to results/tables/ as a csv
def write_csv(df: pd.DataFrame, filename: str) -> None:
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / filename
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Rows)", out.name, len(df))


# monthly counts of questions and answers from the posts table
def monthly_volume(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            SUM(CASE WHEN PostTypeId = 1 THEN 1 ELSE 0 END) AS question_count,
            SUM(CASE WHEN PostTypeId = 2 THEN 1 ELSE 0 END) AS answer_count
        FROM posts
        WHERE CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# monthly count of distinct non-anonymous askers (null owner_user_id is excluded)
def monthly_active_askers(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(DISTINCT OwnerUserId) AS distinct_askers
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# per-month fraction of questions with a non-null accepted_answer_id
def monthly_accepted_rate(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count,
            SUM(CASE WHEN AcceptedAnswerId IS NOT NULL THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS accepted_rate
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# per-month fraction of questions with at least one answer
def monthly_answer_coverage(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count,
            SUM(CASE WHEN COALESCE(AnswerCount, 0) > 0 THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS coverage_rate
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# per-month median and p90 of time-to-first-answer in seconds
def monthly_time_to_first_answer(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        WITH first_answer AS (
            SELECT
                q.Id AS question_id,
                q.CreationDate AS question_created,
                MIN(a.CreationDate) AS first_answered
            FROM posts q
            JOIN posts a ON a.ParentId = q.Id
            WHERE q.PostTypeId = 1
              AND a.PostTypeId = 2
              AND q.CreationDate >= $start_date
            GROUP BY q.Id, q.CreationDate
        )
        SELECT
            strftime(question_created, '%Y-%m') AS year_month,
            COUNT(*) AS answered_count,
            MEDIAN(epoch(first_answered - question_created)) AS median_seconds,
            QUANTILE_CONT(epoch(first_answered - question_created), 0.9) AS p90_seconds
        FROM first_answer
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# per-month median and p90 of time-to-acceptance in seconds
def monthly_time_to_acceptance(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        WITH accepted_pair AS (
            SELECT
                q.Id AS question_id,
                q.CreationDate AS question_created,
                a.CreationDate AS accepted_created
            FROM posts q
            JOIN posts a ON a.Id = q.AcceptedAnswerId
            WHERE q.PostTypeId = 1
              AND q.AcceptedAnswerId IS NOT NULL
              AND q.CreationDate >= $start_date
        )
        SELECT
            strftime(question_created, '%Y-%m') AS year_month,
            COUNT(*) AS accepted_count,
            MEDIAN(epoch(accepted_created - question_created)) AS median_seconds,
            QUANTILE_CONT(epoch(accepted_created - question_created), 0.9) AS p90_seconds
        FROM accepted_pair
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# per-month mean score and mean comment count on questions
def monthly_engagement(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count,
            AVG(Score) AS mean_score,
            AVG(COALESCE(CommentCount, 0)) AS mean_comments
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )


# registry mapping each metric to (compute_fn, csv_filename)
METRICS = {
    "monthly_volume": (monthly_volume, "monthly_volume.csv"),
    "active_askers": (monthly_active_askers, "active_askers.csv"),
    "accepted_rate": (monthly_accepted_rate, "accepted_rate.csv"),
    "answer_coverage": (monthly_answer_coverage, "answer_coverage.csv"),
    "time_to_first_answer": (monthly_time_to_first_answer, "time_to_first_answer.csv"),
    "time_to_acceptance": (monthly_time_to_acceptance, "time_to_acceptance.csv"),
    "engagement": (monthly_engagement, "engagement.csv"),
}


# backward-compat wrappers used by the existing per-metric tests
def write_volume_report() -> None:
    write_csv(monthly_volume(), "monthly_volume.csv")


def write_askers_report() -> None:
    write_csv(monthly_active_askers(), "active_askers.csv")


def write_accepted_report() -> None:
    write_csv(monthly_accepted_rate(), "accepted_rate.csv")


def write_coverage_report() -> None:
    write_csv(monthly_answer_coverage(), "answer_coverage.csv")


def write_response_report() -> None:
    write_csv(monthly_time_to_first_answer(), "time_to_first_answer.csv")


def write_acceptance_report() -> None:
    write_csv(monthly_time_to_acceptance(), "time_to_acceptance.csv")


def write_engagement_report() -> None:
    write_csv(monthly_engagement(), "engagement.csv")


# compute every metric and write its csv
def write_all() -> None:
    for name, (compute_fn, filename) in METRICS.items():
        log.info("Computing %s", name)
        write_csv(compute_fn(), filename)


# main function
def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

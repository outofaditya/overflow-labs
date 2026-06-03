from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.logger import get_logger
from source.data.query import run_query
from source.analysis.metrics import write_csv

log = get_logger(__name__)

# three technology domain groups for rq4
# each maps a domain label to a list of tag substrings (matched case-insensitively)
DOMAIN_GROUPS = {
    "Legacy Stable": [
        "c++", "c#", ".net", "java", "sql", "oracle", "mysql",
        "postgresql", "sql-server", "vb.net", "delphi", "fortran",
        "cobol", "perl", "assembly", "matlab", "objective-c",
        "visual-studio", "wpf", "winforms", "spring", "hibernate",
    ],
    "Fast-Moving Web": [
        "javascript", "typescript", "react", "angular", "vue",
        "node.js", "next.js", "svelte", "webpack", "vite",
        "css", "html", "sass", "tailwind", "bootstrap",
        "express", "nestjs", "nuxt", "remix", "astro",
        "deno", "bun", "npm", "yarn", "pnpm",
    ],
    "AI / ML": [
        "python", "tensorflow", "pytorch", "keras",
        "scikit-learn", "pandas", "numpy", "matplotlib",
        "machine-learning", "deep-learning", "neural-network",
        "nlp", "computer-vision", "opencv", "transformers",
        "huggingface", "langchain", "openai", "gpt",
        "llm", "chatgpt", "stable-diffusion", "rag",
        "vector-database", "embeddings", "fine-tuning",
    ],
}

# build a sql case expression that maps tags to domains
_DOMAIN_CASES = []
for domain, tags in DOMAIN_GROUPS.items():
    conditions = " OR ".join(f"Tags LIKE '%<{tag}>%'" for tag in tags)
    _DOMAIN_CASES.append(f"WHEN ({conditions}) THEN '{domain}'")
_DOMAIN_SQL = "CASE " + " ".join(_DOMAIN_CASES) + " ELSE 'Other' END"


def monthly_volume_by_domain(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        f"""
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            {_DOMAIN_SQL} AS domain,
            COUNT(*) AS question_count
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def monthly_accepted_rate_by_domain(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        f"""
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            {_DOMAIN_SQL} AS domain,
            COUNT(*) AS question_count,
            SUM(CASE WHEN AcceptedAnswerId IS NOT NULL THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS accepted_rate
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def monthly_answer_coverage_by_domain(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        f"""
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            {_DOMAIN_SQL} AS domain,
            COUNT(*) AS question_count,
            SUM(CASE WHEN COALESCE(AnswerCount, 0) > 0 THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS coverage_rate
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def monthly_time_to_first_answer_by_domain(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        f"""
        WITH first_answer AS (
            SELECT
                q.Id AS question_id,
                q.CreationDate AS question_created,
                q.Tags,
                MIN(a.CreationDate) AS first_answered
            FROM posts q
            JOIN posts a ON a.ParentId = q.Id
            WHERE q.PostTypeId = 1
              AND a.PostTypeId = 2
              AND q.CreationDate >= $start_date
            GROUP BY q.Id, q.CreationDate, q.Tags
        )
        SELECT
            strftime(question_created, '%Y-%m') AS year_month,
            {_DOMAIN_SQL.replace('Tags', 'first_answer.Tags')} AS domain,
            COUNT(*) AS answered_count,
            MEDIAN(epoch(first_answered - question_created)) AS median_seconds,
            QUANTILE_CONT(epoch(first_answered - question_created), 0.9) AS p90_seconds
        FROM first_answer
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def monthly_engagement_by_domain(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    return run_query(
        f"""
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            {_DOMAIN_SQL} AS domain,
            COUNT(*) AS question_count,
            AVG(Score) AS mean_score,
            AVG(COALESCE(CommentCount, 0)) AS mean_comments
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def domain_prepost_summary(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    cutoff_str = constants.RELEASE.strftime("%Y-%m-%d")
    return run_query(
        f"""
        SELECT
            {_DOMAIN_SQL} AS domain,
            CASE WHEN CreationDate < '{cutoff_str}' THEN 'pre' ELSE 'post' END AS period,
            COUNT(*) AS question_count,
            SUM(CASE WHEN AcceptedAnswerId IS NOT NULL THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS accepted_rate,
            SUM(CASE WHEN COALESCE(AnswerCount, 0) > 0 THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS coverage_rate,
            AVG(Score) AS mean_score,
            AVG(COALESCE(CommentCount, 0)) AS mean_comments
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        params={"start_date": start},
    )


def domain_volume_change(start: date | None = None) -> pd.DataFrame:
    vol = monthly_volume_by_domain(start)
    cutoff = constants.RELEASE.strftime("%Y-%m")
    vol["period"] = vol["year_month"].apply(lambda ym: "pre" if ym < cutoff else "post")
    summary = (
        vol.groupby(["domain", "period"])["question_count"]
        .agg(["mean", "median", "sum"])
        .reset_index()
    )
    pre = summary[summary["period"] == "pre"].set_index("domain")
    post = summary[summary["period"] == "post"].set_index("domain")
    result = pd.DataFrame(
        {
            "domain": pre.index,
            "pre_mean": pre["mean"].values,
            "post_mean": post.reindex(pre.index)["mean"].values,
            "pct_change_mean": (
                (post.reindex(pre.index)["mean"].values - pre["mean"].values)
                / pre["mean"].values
                * 100
            ),
            "pre_total": pre["sum"].values,
            "post_total": post.reindex(pre.index)["sum"].values,
        }
    )
    return result.reset_index(drop=True)


DOMAIN_METRICS = {
    "domain_volume": (monthly_volume_by_domain, "domain_volume.csv"),
    "domain_accepted_rate": (monthly_accepted_rate_by_domain, "domain_accepted_rate.csv"),
    "domain_coverage": (monthly_answer_coverage_by_domain, "domain_coverage.csv"),
    "domain_response_time": (monthly_time_to_first_answer_by_domain, "domain_response_time.csv"),
    "domain_engagement": (monthly_engagement_by_domain, "domain_engagement.csv"),
    "domain_prepost": (domain_prepost_summary, "domain_prepost_summary.csv"),
    "domain_volume_change": (domain_volume_change, "domain_volume_change.csv"),
}


def write_all() -> None:
    for name, (compute_fn, filename) in DOMAIN_METRICS.items():
        log.info("Computing %s", name)
        write_csv(compute_fn(), filename)


def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

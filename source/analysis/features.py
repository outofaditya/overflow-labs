from __future__ import annotations

import re
import sys
import pandas as pd
from datetime import date
from source import constants
from source.logger import get_logger
from source.data.query import run_query
from source.analysis.parse import parse_body
from source.analysis.metrics import write_csv
from source.analysis.sampling import monthly_sample_plan

# initialize logger
log = get_logger(__name__)

# six per-question lexical features
FEATURES = [
    "title_length",
    "body_prose_length",
    "code_block_count",
    "code_block_total_length",
    "link_count",
    "tag_count",
]

# precompiled link regex avoids a second beautifulsoup pass per row
_LINK_RE = re.compile(r"<a\s", re.IGNORECASE)


# extract the six lex features from a single question's columns
def _features_for_row(title: str | None, body: str | None, tags: str | None) -> dict:
    prose, code_blocks = parse_body(body)
    return {
        "title_length": len(title or ""),
        "body_prose_length": len(prose),
        "code_block_count": len(code_blocks),
        "code_block_total_length": sum(len(b) for b in code_blocks),
        "link_count": len(_LINK_RE.findall(body or "")),
        "tag_count": (tags or "").count("<"),
    }


# get monthly question populations for the analysis window
def _monthly_populations(start: date) -> dict[str, int]:
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS n
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return dict(zip(df["year_month"], df["n"]))


# pull a stratified sample of questions and compute features per row
def per_post_features(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START

    # power analysis: compute required sample per month
    populations = _monthly_populations(start)
    plan = monthly_sample_plan(
        populations,
        alpha=0.05,
        power=0.95,
        effect_size=0.2,
        margin=0.02,
        n_categories=len(FEATURES),
    )
    # use the maximum required n as the SQL cap; for smaller months the
    # query naturally returns the full population (rn <= cap where N < cap)
    cap = max(plan.values())
    log.info("Sample cap per month: %d (power-analysis-based)", cap)

    posts = run_query(
        """
        WITH ranked AS (
            SELECT
                Id, Title, Body, Tags,
                strftime(CreationDate, '%Y-%m') AS year_month,
                row_number() OVER (
                    PARTITION BY strftime(CreationDate, '%Y-%m')
                    ORDER BY hash(Id)
                ) AS rn
            FROM posts
            WHERE PostTypeId = 1 AND CreationDate >= $start_date
        )
        SELECT Id, Title, Body, Tags, year_month
        FROM ranked
        WHERE rn <= $cap
        """,
        params={"start_date": start, "cap": cap},
        max_rows=10_000_000,
    )
    log.info("Computing features for %d questions", len(posts))

    records: list[dict] = []
    for row in posts.itertuples(index=False):
        feats = _features_for_row(row.Title, row.Body, row.Tags)
        feats["year_month"] = row.year_month
        records.append(feats)
    return pd.DataFrame(records)


# aggregate per-post features into median + p90 per month
def monthly_distributions(per_post: pd.DataFrame) -> pd.DataFrame:
    grouped = per_post.groupby("year_month")
    cols: dict[str, pd.Series] = {}
    for feat in FEATURES:
        cols[f"{feat}_median"] = grouped[feat].median()
        cols[f"{feat}_p90"] = grouped[feat].quantile(0.9)
    return pd.DataFrame(cols).reset_index()


# compute and persist the lex feature monthly distributions
def write_features_report() -> None:
    per_post = per_post_features()
    write_csv(per_post, "post_features.csv")
    write_csv(monthly_distributions(per_post), "lex_features.csv")


# main function
def main() -> int:
    write_features_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())

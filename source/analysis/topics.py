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

log = get_logger(__name__)

# beyer et al. seven-category taxonomy extended with two ai-era categories
CATEGORIES = [
    "API Usage",
    "Discrepancy",
    "Errors",
    "Review",
    "Conceptual",
    "API Change",
    "Learning",
    "Machine-Authored Discrepancy",
    "Architectural Consensus",
]

# keyword patterns for each category (applied to title + prose, case-insensitive)
# order matters: first match wins; more specific categories checked first
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # ai-era: machine-authored discrepancy — questions about ai-generated code not working
    (
        "Machine-Authored Discrepancy",
        re.compile(
            r"""(?ix)
            (chatgpt|gpt[-\s]?[34o]|copilot|github\s*copilot|ai[-\s]generat|
             llm|claude|gemini|bard|codewhisperer|code[-\s]?llama|
             ai[-\s]?suggest|ai[-\s]?writ|ai[-\s]?code|generated\s+code|
             ai\s+assistant|large\s+language\s+model)
            """,
        ),
    ),
    # ai-era: architectural consensus — seeking design validation or best-practice consensus
    (
        "Architectural Consensus",
        re.compile(
            r"""(?ix)
            (best\s+(practice|approach|way|pattern|strategy|design|architecture)|
             design\s+pattern|architectural|
             should\s+i\s+use|which\s+(is|approach|pattern|framework)\s+(better|best|preferred)|
             trade[-\s]?off|pros?\s+and\s+cons?|
             recommend(ed|ation)?|
             when\s+to\s+use|
             how\s+to\s+(structure|architect|organiz)|
             scalab(le|ility)|maintain(able|ability))
            """,
        ),
    ),
    # errors: explicit error messages, stack traces, exceptions
    (
        "Errors",
        re.compile(
            r"""(?ix)
            (error\s*:?\s*\w|exception|traceback|stack\s*trace|
             throws?\s|thrown\b|raised?\b|
             segfault|segmentation\s*fault|
             fatal|panic|abort|core\s*dump|
             compilation?\s*(error|fail)|
             syntax\s*error|type\s*error|runtime\s*error|
             name\s*error|value\s*error|key\s*error|
             null\s*pointer|nil\s*pointer|npe|
             undefined\s+is\s+not|cannot\s+read\s+propert|
             unhandled\s+(promise\s+)?reject|
             failed\s+to\s+(compile|build|load|import|install))
            """,
        ),
    ),
    # discrepancy: unexpected behavior, not matching expectations
    (
        "Discrepancy",
        re.compile(
            r"""(?ix)
            (not\s+work(ing|s)?|doesn[''\u2019]?t\s+work|
             unexpected(ly)?|wrong\s+(result|output|answer|value|behavior)|
             incorrect(ly)?|
             bug\b|broken|
             instead\s+of|but\s+(i\s+)?get|but\s+(it\s+)?returns?|
             supposed\s+to|expected\s+to|should\s+(return|be|have|output)|
             doesn[''\u2019]?t\s+(return|match|behave|produce)|
             gives?\s+(me\s+)?(wrong|incorrect|unexpected|different))
            """,
        ),
    ),
    # api change: version migration, deprecation, breaking changes
    (
        "API Change",
        re.compile(
            r"""(?ix)
            (deprecat(ed|ion)|
             migrat(e|ing|ion)|
             upgrade\s+(from|to)|
             breaking\s+change|
             version\s+\d|v\d+\.\d+|
             backward[s]?\s*(in)?compat|
             replac(ed|ement)\s+(by|with|for)|
             no\s+longer\s+(support|available|work)|
             removed\s+(in|from)|
             legacy|
             update[d]?\s+(to|from)\s+(version|v\d))
            """,
        ),
    ),
    # review: asking for code review, optimization, improvement
    (
        "Review",
        re.compile(
            r"""(?ix)
            (review\s+my|code\s+review|
             improv(e|ing|ement)\s+(my|this|the)?\s*(code|performance|solution)|
             optimiz(e|ing|ation)|
             refactor|clean(er|up)|
             is\s+(this|my)\s+(code|approach|solution)\s+(correct|good|efficient|ok)|
             any\s+(better|cleaner|faster|simpler)\s+way|
             more\s+(efficient|elegant|pythonic|idiomatic)|
             feedback\s+on|critique)
            """,
        ),
    ),
    # api usage: how to use a specific api, library, function
    (
        "API Usage",
        re.compile(
            r"""(?ix)
            (how\s+(to|do\s+i|can\s+i)\s+(use|call|invoke|implement|apply|configure|set\s*up)|
             usage\s+of|example\s+of|syntax\s+for|
             using\s+\w+\s+(with|in|for)|
             pass(ing)?\s+\w+\s+to|
             import(ing)?\s+\w+|
             install(ing|ation)?|
             getting\s+started|quick\s*start|
             documentation\s+(for|of|on))
            """,
        ),
    ),
    # conceptual: understanding concepts, theory, internals
    (
        "Conceptual",
        re.compile(
            r"""(?ix)
            (what\s+(is|are|does)|what[''\u2019]s\s+the\s+difference|
             why\s+(is|does|do|are|doesn)|
             how\s+(does|do|is|are)\s+\w+\s+work|
             difference\s+between|
             explain|understand(ing)?|
             meaning\s+of|purpose\s+of|
             concept(ual)?|theory|principle|
             under\s+the\s+hood|internal(ly|s)?|behind\s+the\s+scene)
            """,
        ),
    ),
    # learning: tutorials, resources, getting started
    (
        "Learning",
        re.compile(
            r"""(?ix)
            (tutorial|learn(ing)?|beginner|newbie|starter|
             resource[s]?\s+(for|to|about)|
             recommend\s+(a\s+)?(book|course|tutorial|resource)|
             where\s+(to|can\s+i)\s+(learn|start|find|study)|
             introduction\s+to|intro\s+to|
             for\s+beginners?|new\s+to\s+\w+|
             first\s+time\s+using)
            """,
        ),
    ),
]


def classify_intent(title: str | None, prose: str) -> str:
    text = f"{title or ''} {prose}"
    for category, pattern in _PATTERNS:
        if pattern.search(text):
            return category
    return "API Usage"  # default: most SO questions are usage questions


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


def per_post_intents(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START

    # power analysis: compute required sample per month
    populations = _monthly_populations(start)
    plan = monthly_sample_plan(
        populations,
        alpha=0.05,
        power=0.95,
        effect_size=0.2,
        margin=0.02,
        n_categories=len(CATEGORIES),
    )
    cap = max(plan.values())
    log.info("Sample cap per month: %d (power-analysis-based)", cap)

    posts = run_query(
        """
        WITH ranked AS (
            SELECT
                Id, Title, Body,
                strftime(CreationDate, '%Y-%m') AS year_month,
                row_number() OVER (
                    PARTITION BY strftime(CreationDate, '%Y-%m')
                    ORDER BY hash(Id)
                ) AS rn
            FROM posts
            WHERE PostTypeId = 1 AND CreationDate >= $start_date
        )
        SELECT Id, Title, Body, year_month
        FROM ranked
        WHERE rn <= $cap
        """,
        params={"start_date": start, "cap": cap},
        max_rows=10_000_000,
    )
    log.info("Classifying intent for %d questions", len(posts))

    records: list[dict] = []
    for row in posts.itertuples(index=False):
        prose, _ = parse_body(row.Body)
        intent = classify_intent(row.Title, prose)
        records.append(
            {"year_month": row.year_month, "intent": intent, "post_id": row.Id}
        )
    return pd.DataFrame(records)


def monthly_intent_distribution(per_post: pd.DataFrame) -> pd.DataFrame:
    ct = per_post.groupby(["year_month", "intent"]).size().reset_index(name="count")
    total = ct.groupby("year_month")["count"].transform("sum")
    ct["fraction"] = ct["count"] / total
    return ct.sort_values(["year_month", "intent"]).reset_index(drop=True)


def monthly_intent_wide(per_post: pd.DataFrame) -> pd.DataFrame:
    ct = per_post.groupby(["year_month", "intent"]).size().reset_index(name="count")
    wide = ct.pivot(index="year_month", columns="intent", values="count").fillna(0)
    total = wide.sum(axis=1)
    frac = wide.div(total, axis=0)
    frac.columns = [f"{c}_fraction" for c in frac.columns]
    result = pd.concat([wide, frac], axis=1).reset_index()
    return result


def prepost_intent_summary(per_post: pd.DataFrame) -> pd.DataFrame:
    df = per_post.copy()
    cutoff = pd.Timestamp(constants.RELEASE).strftime("%Y-%m")
    df["period"] = df["year_month"].apply(lambda ym: "pre" if ym < cutoff else "post")
    ct = df.groupby(["period", "intent"]).size().reset_index(name="count")
    total = ct.groupby("period")["count"].transform("sum")
    ct["fraction"] = ct["count"] / total
    return ct.sort_values(["period", "intent"]).reset_index(drop=True)


def write_topics_report() -> None:
    per_post = per_post_intents()
    write_csv(per_post, "post_intents.csv")
    write_csv(monthly_intent_distribution(per_post), "monthly_intent_distribution.csv")
    write_csv(monthly_intent_wide(per_post), "monthly_intent_wide.csv")
    write_csv(prepost_intent_summary(per_post), "prepost_intent_summary.csv")


def main() -> int:
    write_topics_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())

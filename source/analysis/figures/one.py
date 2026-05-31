from __future__ import annotations

import sys
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from source.logger import get_logger
from source.analysis.figures.style import (
    apply,
    PALETTE,
    save_figure,
    legend_patch,
    ACM_2COL_INCHES,
    format_date_axis,
    add_chatgpt_reference,
)

# initialize logger
log = get_logger(__name__)


# load a metric csv and parse year_month into the first-of-month datetime
def _load(filename: str) -> pd.DataFrame:
    df = pd.read_csv(constants.TABLES / filename)
    df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


# decorate axes, save the figure, close — every figure ends here
def _finalize(fig: plt.Figure, name: str, *axes: plt.Axes) -> None:
    for ax in axes:
        format_date_axis(ax)
        add_chatgpt_reference(ax)
    save_figure(fig, name)
    plt.close(fig)


# activity: question+answer volume on the left, distinct askers on the right
def figure_activity() -> None:
    vol = _load("monthly_volume.csv")
    askers = _load("active_askers.csv")
    fig, (ax_vol, ax_askers) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4))

    ax_vol.plot(vol["year_month"], vol["question_count"], color=PALETTE[0])
    ax_vol.plot(vol["year_month"], vol["answer_count"], color=PALETTE[1])
    ax_vol.set_ylabel("Posts per Month")
    ax_vol.legend(
        handles=[
            legend_patch(PALETTE[0], "Questions"),
            legend_patch(PALETTE[1], "Answers"),
        ],
        loc="upper right",
    )

    ax_askers.fill_between(
        askers["year_month"], askers["distinct_askers"], color=PALETTE[0], alpha=0.25
    )
    ax_askers.plot(askers["year_month"], askers["distinct_askers"], color=PALETTE[0])
    ax_askers.set_ylabel("Distinct Askers per Month")

    fig.tight_layout()
    _finalize(fig, "activity", ax_vol, ax_askers)


# quality outcomes: coverage line on top, accepted-rate line below, shaded band = answered-but-not-accepted
def figure_quality() -> None:
    accepted = _load("accepted_rate.csv")
    coverage = _load("answer_coverage.csv")
    merged = accepted.merge(coverage[["year_month", "coverage_rate"]], on="year_month")
    fig, ax = plt.subplots()
    ax.fill_between(
        merged["year_month"],
        merged["accepted_rate"],
        merged["coverage_rate"],
        color=PALETTE[3],
        alpha=0.25,
    )
    ax.plot(merged["year_month"], merged["coverage_rate"], color=PALETTE[3])
    ax.plot(merged["year_month"], merged["accepted_rate"], color=PALETTE[2])
    ax.set_ylabel("Fraction of Questions")
    ax.set_ylim(0, 1)
    ax.legend(
        handles=[
            legend_patch(PALETTE[3], "Coverage"),
            legend_patch(PALETTE[2], "Accepted"),
        ],
        loc="upper right",
    )
    _finalize(fig, "quality", ax)


# response time: time-to-first-answer and time-to-acceptance side-by-side; median line plus p90 band, log scale
def figure_response_time() -> None:
    first = _load("time_to_first_answer.csv")
    accept = _load("time_to_acceptance.csv")
    for df in (first, accept):
        df["median_hours"] = df["median_seconds"] / 3600
        df["p90_hours"] = df["p90_seconds"] / 3600
    fig, (ax_first, ax_accept) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4))

    ax_first.fill_between(
        first["year_month"],
        first["median_hours"],
        first["p90_hours"],
        color=PALETTE[1],
        alpha=0.2,
    )
    ax_first.plot(first["year_month"], first["median_hours"], color=PALETTE[1])
    ax_first.plot(
        first["year_month"],
        first["p90_hours"],
        color=PALETTE[1],
        linewidth=0.8,
        alpha=0.6,
    )
    ax_first.set_yscale("log")
    ax_first.set_ylabel("Hours to First Answer")
    ax_first.legend(
        handles=[
            legend_patch(PALETTE[1], "Median"),
            legend_patch("#EFC3CA", "p90 Range"),
        ],
        loc="lower right",
    )

    ax_accept.fill_between(
        accept["year_month"],
        accept["median_hours"],
        accept["p90_hours"],
        color=PALETTE[5],
        alpha=0.2,
    )
    ax_accept.plot(accept["year_month"], accept["median_hours"], color=PALETTE[5])
    ax_accept.plot(
        accept["year_month"],
        accept["p90_hours"],
        color=PALETTE[5],
        linewidth=0.8,
        alpha=0.6,
    )
    ax_accept.set_yscale("log")
    ax_accept.set_ylabel("Hours to Acceptance")
    ax_accept.legend(
        handles=[
            legend_patch(PALETTE[5], "Median"),
            legend_patch("#DCC5DD", "p90 Range"),
        ],
        loc="lower right",
    )

    fig.tight_layout()
    _finalize(fig, "response_time", ax_first, ax_accept)


# engagement: mean score on the left, mean comments on the right
def figure_engagement() -> None:
    df = _load("engagement.csv")
    fig, (ax_score, ax_comments) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4))

    ax_score.plot(df["year_month"], df["mean_score"], color=PALETTE[0])
    ax_score.set_ylabel("Mean Score")

    ax_comments.fill_between(
        df["year_month"], df["mean_comments"], color=PALETTE[4], alpha=0.3
    )
    ax_comments.plot(df["year_month"], df["mean_comments"], color=PALETTE[4])
    ax_comments.set_ylabel("Mean Comments")

    fig.tight_layout()
    _finalize(fig, "engagement", ax_score, ax_comments)


# generate every rq1 figure in sequence
def write_all() -> None:
    apply()
    log.info("Generating RQ1 Figures")
    figure_activity()
    figure_quality()
    figure_response_time()
    figure_engagement()
    log.info("Done. Output: %s", constants.FIGURES / "one")


# main function
def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

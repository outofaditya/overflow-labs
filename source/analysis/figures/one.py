from __future__ import annotations

import sys
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from source.logger import get_logger
from source.analysis.figures.style import (
    ACM_2COL_INCHES,
    PALETTE,
    add_chatgpt_reference,
    apply,
    format_date_axis,
    legend_patch,
    save_figure,
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


# monthly question and answer volume — two-line chart for comparison
def figure_volume() -> None:
    df = _load("monthly_volume.csv")
    fig, ax = plt.subplots()
    ax.plot(df["year_month"], df["question_count"], color=PALETTE[0])
    ax.plot(df["year_month"], df["answer_count"], color=PALETTE[1])
    ax.set_ylabel("Posts per Month")
    ax.legend(
        handles=[
            legend_patch(PALETTE[0], "Questions"),
            legend_patch(PALETTE[1], "Answers"),
        ],
        loc="upper right",
    )
    _finalize(fig, "volume", ax)


# distinct active askers — filled area emphasises shrinking participation
def figure_active_askers() -> None:
    df = _load("active_askers.csv")
    fig, ax = plt.subplots()
    ax.fill_between(
        df["year_month"], df["distinct_askers"], color=PALETTE[0], alpha=0.25
    )
    ax.plot(df["year_month"], df["distinct_askers"], color=PALETTE[0])
    ax.set_ylabel("Distinct Askers per Month")
    _finalize(fig, "active_askers", ax)


# accepted-answer rate — filled area expresses fraction
def figure_accepted_rate() -> None:
    df = _load("accepted_rate.csv")
    fig, ax = plt.subplots()
    ax.fill_between(df["year_month"], df["accepted_rate"], color=PALETTE[2], alpha=0.25)
    ax.plot(df["year_month"], df["accepted_rate"], color=PALETTE[2])
    ax.set_ylabel("Fraction Accepted")
    ax.set_ylim(0, 1)
    _finalize(fig, "accepted_rate", ax)


# answer coverage rate — same chart type as accepted_rate for direct comparison
def figure_answer_coverage() -> None:
    df = _load("answer_coverage.csv")
    fig, ax = plt.subplots()
    ax.fill_between(df["year_month"], df["coverage_rate"], color=PALETTE[3], alpha=0.3)
    ax.plot(df["year_month"], df["coverage_rate"], color=PALETTE[3])
    ax.set_ylabel("Fraction With Any Answer")
    ax.set_ylim(0, 1)
    _finalize(fig, "answer_coverage", ax)


# time-to-first-answer — median line with shaded p90 band
def figure_time_to_first_answer() -> None:
    df = _load("time_to_first_answer.csv")
    df["median_hours"] = df["median_seconds"] / 3600
    df["p90_hours"] = df["p90_seconds"] / 3600
    fig, ax = plt.subplots()
    ax.fill_between(
        df["year_month"],
        df["median_hours"],
        df["p90_hours"],
        color=PALETTE[1],
        alpha=0.2,
    )
    ax.plot(df["year_month"], df["median_hours"], color=PALETTE[1])
    ax.plot(
        df["year_month"], df["p90_hours"], color=PALETTE[1], linewidth=0.8, alpha=0.6
    )
    ax.set_yscale("log")
    ax.set_ylabel("Hours to First Answer")
    ax.legend(
        handles=[
            legend_patch(PALETTE[1], "Median"),
            legend_patch("#EFC3CA", "p90 Range"),
        ],
        loc="lower right",
    )
    _finalize(fig, "time_to_first_answer", ax)


# time-to-acceptance — same chart type as time_to_first_answer for direct comparison
def figure_time_to_acceptance() -> None:
    df = _load("time_to_acceptance.csv")
    df["median_hours"] = df["median_seconds"] / 3600
    df["p90_hours"] = df["p90_seconds"] / 3600
    fig, ax = plt.subplots()
    ax.fill_between(
        df["year_month"],
        df["median_hours"],
        df["p90_hours"],
        color=PALETTE[5],
        alpha=0.2,
    )
    ax.plot(df["year_month"], df["median_hours"], color=PALETTE[5])
    ax.plot(
        df["year_month"], df["p90_hours"], color=PALETTE[5], linewidth=0.8, alpha=0.6
    )
    ax.set_yscale("log")
    ax.set_ylabel("Hours to Acceptance")
    ax.legend(
        handles=[
            legend_patch(PALETTE[5], "Median"),
            legend_patch("#DCC5DD", "p90 Range"),
        ],
        loc="lower right",
    )
    _finalize(fig, "time_to_acceptance", ax)


# engagement — side-by-side subplots; line on left, filled area on right for visual variety
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
    log.info("Generating RQ1 figures")
    figure_volume()
    figure_active_askers()
    figure_accepted_rate()
    figure_answer_coverage()
    figure_time_to_first_answer()
    figure_time_to_acceptance()
    figure_engagement()
    log.info("Done. Output: %s", constants.FIGURES / "rq1")


# main function
def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

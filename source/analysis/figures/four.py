from __future__ import annotations

import sys
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from source.logger import get_logger
from source.analysis.domains import DOMAIN_GROUPS
from source.analysis.figures.style import (
    apply,
    PALETTE,
    EDGE_COLOR,
    save_figure,
    legend_patch,
    ACM_2COL_INCHES,
    format_date_axis,
    add_chatgpt_reference,
)

log = get_logger(__name__)

# consistent colors per domain
_DOMAIN_COLORS = {
    "Legacy Stable": PALETTE[0],
    "Fast-Moving Web": PALETTE[1],
    "AI / ML": PALETTE[2],
    "Other": PALETTE[6],
}

_DOMAINS_ORDERED = ["Legacy Stable", "Fast-Moving Web", "AI / ML", "Other"]


def _load(filename: str) -> pd.DataFrame:
    df = pd.read_csv(constants.TABLES / filename)
    if "year_month" in df.columns:
        df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


def figure_domain_volume() -> None:
    df = _load("domain_volume.csv")
    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.8))

    for domain in _DOMAINS_ORDERED:
        subset = df[df["domain"] == domain].sort_values("year_month")
        if subset.empty:
            continue
        color = _DOMAIN_COLORS.get(domain, PALETTE[6])
        ax.plot(subset["year_month"], subset["question_count"], color=color, label=domain)

    ax.set_ylabel("Questions per Month")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    format_date_axis(ax)
    add_chatgpt_reference(ax)
    fig.tight_layout()
    save_figure(fig, "domain_volume", group="four")
    plt.close(fig)


def figure_domain_volume_normalized() -> None:
    df = _load("domain_volume.csv")
    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.8))

    for domain in _DOMAINS_ORDERED:
        subset = df[df["domain"] == domain].sort_values("year_month").copy()
        if subset.empty or subset["question_count"].iloc[0] == 0:
            continue
        baseline = subset["question_count"].iloc[0]
        subset["normalized"] = subset["question_count"] / baseline * 100
        color = _DOMAIN_COLORS.get(domain, PALETTE[6])
        ax.plot(subset["year_month"], subset["normalized"], color=color, label=domain)

    ax.axhline(100, color=EDGE_COLOR, linewidth=0.5, linestyle=":")
    ax.set_ylabel("Volume (Jan 2020 = 100)")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    format_date_axis(ax)
    add_chatgpt_reference(ax)
    fig.tight_layout()
    save_figure(fig, "domain_volume_normalized", group="four")
    plt.close(fig)


def figure_domain_quality() -> None:
    acc = _load("domain_accepted_rate.csv")
    cov = _load("domain_coverage.csv")

    fig, (ax_acc, ax_cov) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4), sharey=True)

    for domain in _DOMAINS_ORDERED:
        color = _DOMAIN_COLORS.get(domain, PALETTE[6])
        sub_acc = acc[acc["domain"] == domain].sort_values("year_month")
        sub_cov = cov[cov["domain"] == domain].sort_values("year_month")
        if not sub_acc.empty:
            ax_acc.plot(sub_acc["year_month"], sub_acc["accepted_rate"], color=color)
        if not sub_cov.empty:
            ax_cov.plot(sub_cov["year_month"], sub_cov["coverage_rate"], color=color)

    ax_acc.set_ylabel("Rate")
    ax_acc.set_title("Accepted Rate", fontsize=7)
    ax_cov.set_title("Coverage Rate", fontsize=7)
    ax_acc.set_ylim(0, 1)

    handles = [legend_patch(c, d) for d, c in _DOMAIN_COLORS.items()]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False, fontsize=6)

    for ax in (ax_acc, ax_cov):
        format_date_axis(ax)
        add_chatgpt_reference(ax, with_label=False)

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_figure(fig, "domain_quality", group="four")
    plt.close(fig)


def figure_domain_response_time() -> None:
    df = _load("domain_response_time.csv")
    df["median_hours"] = df["median_seconds"] / 3600

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.8))

    for domain in _DOMAINS_ORDERED:
        subset = df[df["domain"] == domain].sort_values("year_month")
        if subset.empty:
            continue
        color = _DOMAIN_COLORS.get(domain, PALETTE[6])
        ax.plot(subset["year_month"], subset["median_hours"], color=color, label=domain)

    ax.set_yscale("log")
    ax.set_ylabel("Median Hours to First Answer")
    ax.legend(frameon=False, fontsize=7)
    format_date_axis(ax)
    add_chatgpt_reference(ax)
    fig.tight_layout()
    save_figure(fig, "domain_response_time", group="four")
    plt.close(fig)


def figure_domain_engagement() -> None:
    df = _load("domain_engagement.csv")

    fig, (ax_score, ax_comments) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4))

    for domain in _DOMAINS_ORDERED:
        color = _DOMAIN_COLORS.get(domain, PALETTE[6])
        subset = df[df["domain"] == domain].sort_values("year_month")
        if subset.empty:
            continue
        ax_score.plot(subset["year_month"], subset["mean_score"], color=color)
        ax_comments.plot(subset["year_month"], subset["mean_comments"], color=color)

    ax_score.set_ylabel("Mean Score")
    ax_comments.set_ylabel("Mean Comments")
    ax_score.set_title("Score by Domain", fontsize=7)
    ax_comments.set_title("Comments by Domain", fontsize=7)

    handles = [legend_patch(c, d) for d, c in _DOMAIN_COLORS.items()]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False, fontsize=6)

    for ax in (ax_score, ax_comments):
        format_date_axis(ax)
        add_chatgpt_reference(ax, with_label=False)

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_figure(fig, "domain_engagement", group="four")
    plt.close(fig)


def figure_domain_volume_change() -> None:
    df = _load("domain_volume_change.csv")
    df = df[df["domain"] != "Other"].sort_values("pct_change_mean")

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.0))
    colors = [_DOMAIN_COLORS.get(d, PALETTE[6]) for d in df["domain"]]
    bars = ax.barh(df["domain"], df["pct_change_mean"], color=colors, edgecolor=EDGE_COLOR, linewidth=0.7)
    ax.axvline(0, color=EDGE_COLOR, linewidth=0.8)
    ax.set_xlabel("Mean Monthly Volume Change (%)")
    ax.yaxis.grid(False)

    for bar, value in zip(bars, df["pct_change_mean"]):
        pad = abs(value) * 0.02 + 1
        x_text = bar.get_width() + (pad if value >= 0 else -pad)
        ha = "left" if value >= 0 else "right"
        ax.text(x_text, bar.get_y() + bar.get_height() / 2, f"{value:+.1f}%", va="center", ha=ha, fontsize=7)

    fig.tight_layout()
    save_figure(fig, "domain_volume_change", group="four")
    plt.close(fig)


def write_all() -> None:
    apply()
    log.info("Generating RQ4 Figures")
    figure_domain_volume()
    figure_domain_volume_normalized()
    figure_domain_quality()
    figure_domain_response_time()
    figure_domain_engagement()
    figure_domain_volume_change()
    log.info("Done. Output: %s", constants.FIGURES / "four")


def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

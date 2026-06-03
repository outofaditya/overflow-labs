from __future__ import annotations

import sys
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from source.logger import get_logger
from source.analysis.topics import CATEGORIES
from source.analysis.figures.style import (
    apply,
    PALETTE,
    REFERENCE_COLOR,
    save_figure,
    ACM_2COL_INCHES,
    format_date_axis,
    add_chatgpt_reference,
)

log = get_logger(__name__)

# extended palette for 9 categories (paul tol bright + muted fills)
_CAT_COLORS = PALETTE + ["#332288", "#44AA99"]


def _load(filename: str) -> pd.DataFrame:
    df = pd.read_csv(constants.TABLES / filename)
    if "year_month" in df.columns:
        df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


def figure_intent_trends() -> None:
    df = _load("monthly_intent_distribution.csv")
    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 3.2))

    for i, cat in enumerate(CATEGORIES):
        subset = df[df["intent"] == cat].sort_values("year_month")
        if subset.empty:
            continue
        color = _CAT_COLORS[i % len(_CAT_COLORS)]
        ax.plot(subset["year_month"], subset["fraction"], color=color, label=cat)

    ax.set_ylabel("Fraction of Questions")
    ax.set_ylim(0, None)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=6,
        frameon=False,
    )
    format_date_axis(ax)
    add_chatgpt_reference(ax)
    fig.tight_layout()
    save_figure(fig, "intent_trends", group="three")
    plt.close(fig)


def figure_intent_stacked() -> None:
    wide = _load("monthly_intent_wide.csv")
    frac_cols = [c for c in wide.columns if c.endswith("_fraction")]
    # sort categories by overall prevalence (largest at bottom of stack)
    totals = wide[frac_cols].mean().sort_values(ascending=False)
    ordered_cols = list(totals.index)
    labels = [c.replace("_fraction", "") for c in ordered_cols]

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 3.2))
    bottom = pd.Series(0.0, index=wide.index)
    for i, col in enumerate(ordered_cols):
        color = _CAT_COLORS[i % len(_CAT_COLORS)]
        vals = wide[col].fillna(0)
        ax.fill_between(wide["year_month"], bottom, bottom + vals, color=color, alpha=0.7)
        bottom = bottom + vals

    ax.set_ylabel("Cumulative Fraction")
    ax.set_ylim(0, 1)

    handles = [
        plt.Rectangle((0, 0), 1, 1, fc=_CAT_COLORS[i % len(_CAT_COLORS)], alpha=0.7)
        for i in range(len(ordered_cols))
    ]
    ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=6,
        frameon=False,
    )
    format_date_axis(ax)
    add_chatgpt_reference(ax)
    fig.tight_layout()
    save_figure(fig, "intent_stacked", group="three")
    plt.close(fig)


def figure_intent_prepost() -> None:
    df = _load("prepost_intent_summary.csv")

    categories = sorted(df["intent"].unique())
    pre = df[df["period"] == "pre"].set_index("intent").reindex(categories)
    post = df[df["period"] == "post"].set_index("intent").reindex(categories)

    x = range(len(categories))
    width = 0.35

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 3.0))
    ax.bar(
        [xi - width / 2 for xi in x],
        pre["fraction"].fillna(0),
        width,
        label="Pre-ChatGPT",
        color=PALETTE[0],
        edgecolor="#222222",
        linewidth=0.5,
    )
    ax.bar(
        [xi + width / 2 for xi in x],
        post["fraction"].fillna(0),
        width,
        label="Post-ChatGPT",
        color=PALETTE[1],
        edgecolor="#222222",
        linewidth=0.5,
    )

    ax.set_ylabel("Fraction of Questions")
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, rotation=45, ha="right", fontsize=6)
    ax.legend(frameon=False, fontsize=7)
    ax.yaxis.grid(True)
    ax.xaxis.grid(False)

    fig.tight_layout()
    save_figure(fig, "intent_prepost", group="three")
    plt.close(fig)


def figure_ai_categories() -> None:
    df = _load("monthly_intent_distribution.csv")
    ai_cats = ["Machine-Authored Discrepancy", "Architectural Consensus"]

    fig, axes = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.4), sharey=True)
    for ax, cat, color in zip(axes, ai_cats, [PALETTE[5], PALETTE[4]]):
        subset = df[df["intent"] == cat].sort_values("year_month")
        if subset.empty:
            ax.set_title(cat, fontsize=7)
            continue
        ax.fill_between(subset["year_month"], subset["fraction"], color=color, alpha=0.3)
        ax.plot(subset["year_month"], subset["fraction"], color=color)
        ax.set_title(cat, fontsize=7)
        ax.set_ylabel("Fraction")
        format_date_axis(ax)
        add_chatgpt_reference(ax, with_label=False)

    fig.tight_layout()
    save_figure(fig, "ai_categories", group="three")
    plt.close(fig)


def write_all() -> None:
    apply()
    log.info("Generating RQ3 Figures")
    figure_intent_trends()
    figure_intent_stacked()
    figure_intent_prepost()
    figure_ai_categories()
    log.info("Done. Output: %s", constants.FIGURES / "three")


def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

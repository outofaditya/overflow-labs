from __future__ import annotations

import sys
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from source.logger import get_logger
from source.analysis.figures.style import (
    apply,
    PALETTE,
    EDGE_COLOR,
    REFERENCE_COLOR,
    save_figure,
    ACM_2COL_INCHES,
    format_date_axis,
    add_chatgpt_reference,
)

# initialize logger
log = get_logger(__name__)


# top row groups length features; bottom row groups structure-count features
_FEATURES: list[tuple[str, str, str]] = [
    ("title_length", "Title Length (chars)", PALETTE[0]),
    ("body_prose_length", "Body Prose Length (chars)", PALETTE[1]),
    ("code_block_total_length", "Code Block Length (chars)", PALETTE[2]),
    ("code_block_count", "Code Block Count", PALETTE[3]),
    ("link_count", "Link Count", PALETTE[4]),
    ("tag_count", "Tag Count", PALETTE[5]),
]


# load lex features csv and parse year_month into first-of-month datetime
def _load() -> pd.DataFrame:
    df = pd.read_csv(constants.TABLES / "lex_features.csv")
    df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


# 2x3 small-multiples panel of all six features over time, with a single shared legend at the top
def figure_timeline() -> None:
    df = _load()
    fig, axes = plt.subplots(2, 3, figsize=(ACM_2COL_INCHES, 4.6), sharex=True)
    for ax, (feat, label, color) in zip(axes.flat, _FEATURES):
        median = df[f"{feat}_median"]
        p90 = df[f"{feat}_p90"]
        ax.fill_between(df["year_month"], median, p90, color=color, alpha=0.2)
        ax.plot(df["year_month"], median, color=color)
        ax.plot(df["year_month"], p90, color=color, linewidth=0.8, alpha=0.6)
        ax.set_ylabel(label)
        # step=2 keeps year ticks readable in narrow small-multiples panels
        format_date_axis(ax, step=2)
        # suppress the per-panel rotated label; the legend covers it
        add_chatgpt_reference(ax, with_label=False)

    fig.legend(
        handles=[
            Line2D([0], [0], color="#666666", linewidth=1.7, label="Monthly Median"),
            Patch(facecolor="#aaaaaa", alpha=0.4, label="p90 Range"),
            Line2D(
                [0],
                [0],
                color=REFERENCE_COLOR,
                linestyle="--",
                linewidth=0.8,
                label="GPT Release",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=3,
        frameon=False,
    )
    # reserve top strip for the figure legend
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save_figure(fig, "complexity_trends", group="two")
    plt.close(fig)


# horizontal bar chart of percent change in monthly-median between pre and post chatgpt release
def figure_prepost() -> None:
    df = _load()
    cutoff = pd.Timestamp(constants.RELEASE)
    pre = df[df["year_month"] < cutoff]
    post = df[df["year_month"] >= cutoff]

    items: list[tuple[str, float]] = []
    for feat, label, _ in _FEATURES:
        col = f"{feat}_median"
        pre_mean = float(pre[col].mean())
        post_mean = float(post[col].mean())
        pct = (post_mean - pre_mean) / pre_mean * 100.0 if pre_mean else 0.0
        # strip unit suffix from category labels for compactness
        items.append((label.split(" (")[0], pct))

    # ascending sort so the biggest decline sits at the bottom and biggest gain sits at the top
    items.sort(key=lambda r: r[1])
    labels = [r[0] for r in items]
    changes = [r[1] for r in items]
    colors = [PALETTE[2] if c >= 0 else PALETTE[1] for c in changes]

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.8))
    bars = ax.barh(labels, changes, color=colors, edgecolor=EDGE_COLOR, linewidth=0.7)
    ax.axvline(0, color=EDGE_COLOR, linewidth=0.8)
    ax.set_xlabel("Change vs Pre-Release (%)")
    # the horizontal-bar y-axis is categorical; only the x-axis grid carries meaning
    ax.yaxis.grid(False)

    # xlim must include x=0 so bars visually anchor to the y-axis; pad only on sides that carry value labels
    lo = min(min(changes), 0.0)
    hi = max(max(changes), 0.0)
    span = max(hi - lo, 1e-9)
    left_pad = span * 0.12 if any(c < 0 for c in changes) else 0.0
    right_pad = span * 0.12 if any(c > 0 for c in changes) else 0.0
    ax.set_xlim(lo - left_pad, hi + right_pad)

    label_pad = span * 0.015
    for bar, value in zip(bars, changes):
        x_text = bar.get_width() + (label_pad if value >= 0 else -label_pad)
        ha = "left" if value >= 0 else "right"
        ax.text(
            x_text,
            bar.get_y() + bar.get_height() / 2,
            f"{value:+.1f}%",
            va="center",
            ha=ha,
            fontsize=7,
        )

    fig.tight_layout()
    save_figure(fig, "complexity_change", group="two")
    plt.close(fig)


# generate every rq2-prep figure in sequence
def write_all() -> None:
    apply()
    log.info("Generating RQ2-Prep Figures")
    figure_timeline()
    figure_prepost()
    log.info("Done. Output: %s", constants.FIGURES / "two")


# main function
def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

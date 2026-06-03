from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from source import constants
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from source.logger import get_logger
from source.analysis.temporal import SERIES_SPECS, _load_series, _breakpoint_index
from source.analysis.figures.style import (
    apply,
    PALETTE,
    EDGE_COLOR,
    REFERENCE_COLOR,
    save_figure,
    ACM_2COL_INCHES,
    ACM_COL_INCHES,
    format_date_axis,
    add_chatgpt_reference,
)

log = get_logger(__name__)


def figure_its_fits() -> None:
    specs = [s for s in SERIES_SPECS if (constants.TABLES / s[0]).exists()]
    n_specs = len(specs)
    if n_specs == 0:
        log.warning("No metric CSVs found, skipping ITS figure")
        return

    ncols = 3
    nrows = (n_specs + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ACM_2COL_INCHES, nrows * 1.8), sharex=True)
    axes_flat = axes.flat if hasattr(axes, "flat") else [axes]

    for idx, (filename, column, label) in enumerate(specs):
        ax = axes_flat[idx]
        series = _load_series(filename, column)
        y = series.values.astype(float)
        n = len(y)
        bp = _breakpoint_index(series)

        t = np.arange(n, dtype=float)
        D = np.zeros(n)
        D[bp:] = 1.0
        T_post = np.zeros(n)
        T_post[bp:] = np.arange(n - bp, dtype=float)

        X = np.column_stack([np.ones(n), t, D, T_post])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        y_hat = X @ beta

        ax.plot(series.index, y, color=PALETTE[0], linewidth=1.0, alpha=0.7)
        # pre-break fit
        ax.plot(series.index[:bp], y_hat[:bp], color=PALETTE[1], linewidth=1.5, linestyle="--")
        # post-break fit
        ax.plot(series.index[bp:], y_hat[bp:], color=PALETTE[2], linewidth=1.5, linestyle="--")
        ax.set_title(label, fontsize=6, pad=3)
        format_date_axis(ax, step=2)
        add_chatgpt_reference(ax, with_label=False)

    # hide unused axes
    for idx in range(n_specs, len(list(axes_flat))):
        axes_flat[idx].set_visible(False)

    fig.legend(
        handles=[
            Line2D([0], [0], color=PALETTE[0], linewidth=1.0, alpha=0.7, label="Observed"),
            Line2D([0], [0], color=PALETTE[1], linewidth=1.5, linestyle="--", label="Pre-break fit"),
            Line2D([0], [0], color=PALETTE[2], linewidth=1.5, linestyle="--", label="Post-break fit"),
            Line2D([0], [0], color=REFERENCE_COLOR, linewidth=0.8, linestyle="--", label="GPT Release"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=4,
        frameon=False,
        fontsize=6,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save_figure(fig, "its_fits", group="five")
    plt.close(fig)


def figure_chow_summary() -> None:
    path = constants.TABLES / "chow_test.csv"
    if not path.exists():
        log.warning("chow_test.csv not found, skipping figure")
        return

    df = pd.read_csv(path)
    df = df.sort_values("f_statistic", ascending=True)

    fig, ax = plt.subplots(figsize=(ACM_2COL_INCHES, 2.4))
    colors = [PALETTE[2] if p < 0.05 else PALETTE[6] for p in df["p_value"]]
    bars = ax.barh(df["metric"], df["f_statistic"], color=colors, edgecolor=EDGE_COLOR, linewidth=0.7)
    ax.set_xlabel("Chow F-statistic")
    ax.yaxis.grid(False)

    for bar, p in zip(bars, df["p_value"]):
        x_text = bar.get_width() + max(bar.get_width() * 0.02, 0.5)
        label = f"p={p:.4f}" if p >= 0.0001 else "p<0.0001"
        ax.text(x_text, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=6)

    fig.tight_layout()
    save_figure(fig, "chow_summary", group="five")
    plt.close(fig)


def figure_cusum_paths() -> None:
    specs = [s for s in SERIES_SPECS if (constants.TABLES / s[0]).exists()]
    n_specs = len(specs)
    if n_specs == 0:
        return

    ncols = 3
    nrows = (n_specs + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ACM_2COL_INCHES, nrows * 1.8), sharex=True)
    axes_flat = axes.flat if hasattr(axes, "flat") else [axes]

    for idx, (filename, column, label) in enumerate(specs):
        ax = axes_flat[idx]
        series = _load_series(filename, column)
        y = series.values.astype(float)
        n = len(y)

        t = np.arange(n, dtype=float)
        X = np.column_stack([np.ones(n), t])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        residuals = y - X @ beta
        sigma = float(np.std(residuals, ddof=2))
        if sigma < 1e-15:
            sigma = 1.0
        cumsum = np.cumsum(residuals) / sigma

        # critical bounds (5% level, brownian bridge approximation)
        critical = 0.948 * np.sqrt(n)

        ax.plot(series.index, cumsum, color=PALETTE[0], linewidth=1.0)
        ax.axhline(critical, color=PALETTE[1], linewidth=0.8, linestyle="--", alpha=0.7)
        ax.axhline(-critical, color=PALETTE[1], linewidth=0.8, linestyle="--", alpha=0.7)
        ax.axhline(0, color=EDGE_COLOR, linewidth=0.5, alpha=0.5)
        ax.set_title(label, fontsize=6, pad=3)
        format_date_axis(ax, step=2)
        add_chatgpt_reference(ax, with_label=False)

    for idx in range(n_specs, len(list(axes_flat))):
        axes_flat[idx].set_visible(False)

    fig.legend(
        handles=[
            Line2D([0], [0], color=PALETTE[0], linewidth=1.0, label="CUSUM"),
            Line2D([0], [0], color=PALETTE[1], linewidth=0.8, linestyle="--", label="5% Bounds"),
            Line2D([0], [0], color=REFERENCE_COLOR, linewidth=0.8, linestyle="--", label="GPT Release"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=3,
        frameon=False,
        fontsize=6,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save_figure(fig, "cusum_paths", group="five")
    plt.close(fig)


def figure_its_coefficients() -> None:
    path = constants.TABLES / "its_regression.csv"
    if not path.exists():
        log.warning("its_regression.csv not found, skipping figure")
        return

    df = pd.read_csv(path)

    fig, (ax_level, ax_slope) = plt.subplots(1, 2, figsize=(ACM_2COL_INCHES, 2.8))

    df_sorted = df.sort_values("level_change_coef")
    colors_level = [PALETTE[2] if p < 0.05 else PALETTE[6] for p in df_sorted["level_change_p"]]
    ax_level.barh(df_sorted["metric"], df_sorted["level_change_coef"], color=colors_level, edgecolor=EDGE_COLOR, linewidth=0.5)
    ax_level.axvline(0, color=EDGE_COLOR, linewidth=0.8)
    ax_level.set_xlabel("Level Change Coefficient")
    ax_level.set_title("Level Shift at Breakpoint", fontsize=7)
    ax_level.yaxis.grid(False)

    df_sorted2 = df.sort_values("slope_change_coef")
    colors_slope = [PALETTE[2] if p < 0.05 else PALETTE[6] for p in df_sorted2["slope_change_p"]]
    ax_slope.barh(df_sorted2["metric"], df_sorted2["slope_change_coef"], color=colors_slope, edgecolor=EDGE_COLOR, linewidth=0.5)
    ax_slope.axvline(0, color=EDGE_COLOR, linewidth=0.8)
    ax_slope.set_xlabel("Slope Change Coefficient")
    ax_slope.set_title("Slope Change at Breakpoint", fontsize=7)
    ax_slope.yaxis.grid(False)

    fig.tight_layout()
    save_figure(fig, "its_coefficients", group="five")
    plt.close(fig)


def write_all() -> None:
    apply()
    log.info("Generating §4.5 Temporal Statistics Figures")
    figure_its_fits()
    figure_chow_summary()
    figure_cusum_paths()
    figure_its_coefficients()
    log.info("Done. Output: %s", constants.FIGURES / "five")


def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

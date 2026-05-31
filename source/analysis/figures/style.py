from __future__ import annotations

import matplotlib as mpl
from source import constants
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

# paul tol's bright palette: color-blind safe, designed for scientific publishing
PALETTE = [
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#BBBBBB",
]

# acm figure widths
ACM_COL_INCHES = 3.33
ACM_2COL_INCHES = 7.00

# shared chart colors used in multiple helpers
EDGE_COLOR = "#222222"
REFERENCE_COLOR = "#444444"


def apply() -> None:
    mpl.rcParams.update(
        {
            # font: verdana is preinstalled on macos and windows; liberation sans on linux
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Verdana",
                "DejaVu Sans",
                "Liberation Sans",
                "Arial",
                "sans-serif",
            ],
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.labelweight": "bold",
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "legend.frameon": False,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "axes.linewidth": 0.7,
            "axes.edgecolor": EDGE_COLOR,
            "axes.axisbelow": True,
            "axes.grid": True,
            "axes.grid.axis": "both",
            "grid.color": "#cccccc",
            "grid.alpha": 0.9,
            "grid.linestyle": (0, (4, 2)),
            "grid.linewidth": 0.5,
            # data lines
            "lines.linewidth": 1.7,
            "lines.solid_capstyle": "round",
            # figure
            "figure.figsize": (ACM_COL_INCHES, 2.4),
            "figure.dpi": 110,
            "savefig.bbox": "tight",
            "savefig.format": "svg",
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
        }
    )


# year-only x-axis tick formatting
def format_date_axis(ax: plt.Axes) -> None:
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# save the figure as svg under results/figures/<group>/<name>.svg
def save_figure(fig: plt.Figure, name: str, group: str = "one") -> None:
    out_dir = constants.FIGURES / group
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.svg")


# draw the chatgpt release vertical reference line with a rotated label
def add_chatgpt_reference(ax: plt.Axes, label: str = "GPT Release") -> None:
    ax.axvline(
        constants.RELEASE,
        color=REFERENCE_COLOR,
        linestyle="--",
        linewidth=0.8,
        alpha=0.9,
        zorder=2,
    )
    ax.annotate(
        label,
        xy=(constants.RELEASE, 0.97),
        xycoords=("data", "axes fraction"),
        xytext=(3, 0),
        textcoords="offset points",
        fontsize=7,
        fontweight="medium",
        va="top",
        ha="left",
        rotation=90,
        color=REFERENCE_COLOR,
        zorder=3,
    )


# build a square filled patch suitable as a legend handle
def legend_patch(color: str, label: str) -> Patch:
    return Patch(facecolor=color, edgecolor=EDGE_COLOR, linewidth=0.7, label=label)

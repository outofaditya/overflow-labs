from __future__ import annotations

import matplotlib as mpl
from datetime import date
from source import constants
import matplotlib.pyplot as plt

# apple's classic color palette (used for simple, friendly visuals)
PALETTE = [
    "#FC6255",
    "#53BDEB",
    "#FFC135",
    "#A0E060",
    "#AF52DE",
    "#FFD3E2",
    "#86868B",
]

# acm figure widths
ACM_COL_INCHES = 3.33
ACM_2COL_INCHES = 7.00

# the chatgpt release used as a vertical reference line in every rq1 chart
CHATGPT_RELEASE = date(2022, 11, 30)


# apply publication-grade matplotlib rcparams for the acm 2-column template
def apply() -> None:
    mpl.rcParams.update(
        {
            # font: linux libertine matches the modern acmart class; serif fallbacks for portability
            "font.family": "serif",
            "font.serif": [
                "Linux Libertine",
                "STIX Two Text",
                "Times New Roman",
                "Times",
                "serif",
            ],
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            # axes look
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
            "lines.linewidth": 1.2,
            # figure
            "figure.figsize": (ACM_COL_INCHES, 2.3),
            "figure.dpi": 100,
            "savefig.bbox": "tight",
            "savefig.format": "svg",
            # color cycle
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
        }
    )


# save the figure as svg under results/figures/<group>/<name>.svg
def save_figure(fig: plt.Figure, name: str, group: str = "rq1") -> None:
    out_dir = constants.FIGURES / group
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.svg"
    fig.savefig(out)


# draw the chatgpt release vertical reference line and a small label
def add_chatgpt_reference(ax: plt.Axes, label: str = "ChatGPT release") -> None:
    ax.axvline(
        CHATGPT_RELEASE, color="#666666", linestyle=":", linewidth=0.8, alpha=0.8
    )
    ymin, ymax = ax.get_ylim()
    ax.text(
        CHATGPT_RELEASE,
        ymax,
        f" {label}",
        fontsize=6,
        va="top",
        ha="left",
        color="#666666",
    )

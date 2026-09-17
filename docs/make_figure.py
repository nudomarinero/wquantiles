"""Regenerate the README figure.

    uv run --group docs python docs/make_figure.py

Draws how a weighted quantile is actually computed, and how the answer differs
from the discrete definition that ``np.quantile(..., weights=...)`` implements.
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import wquantiles

HERE = __import__("pathlib").Path(__file__).parent

DATA = np.array([1.0, 2.0, 3.0, 5.0, 8.0])
WEIGHTS = np.array([1.0, 3.0, 1.0, 4.0, 2.0])
Q = 0.5

INK = "#1b1f24"
MUTED = "#57606a"
SLAB = "#9ec5fe"
CURVE = "#0a58ca"
ACCENT = "#c2410c"
DISCRETE = "#15803d"
GRID = "#e6e8eb"


def weighted_ecdf(data, weights):
    """The arrays the algorithm actually builds."""
    order = np.lexsort((weights, data))
    values, w = data[order], weights[order]
    upper = np.cumsum(w) / w.sum()
    lower = upper - w / w.sum()
    midpoints = (lower + upper) / 2  # this is Pn = (Sn - 0.5w) / Sn[-1]
    return values, w, lower, upper, midpoints


def style(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def panel_construction(ax):
    values, w, lower, upper, mid = weighted_ecdf(DATA, WEIGHTS)
    result = wquantiles.quantile_1D(DATA, WEIGHTS, Q)

    # Each value owns a slab of probability as tall as its weight.
    for x, lo, hi, weight in zip(values, lower, upper, w):
        ax.plot([x, x], [lo, hi], color=SLAB, linewidth=11,
                solid_capstyle="butt", zorder=2)
        ax.annotate(f"w={weight:g}", (x, (lo + hi) / 2), xytext=(9, 0),
                    textcoords="offset points", fontsize=8, color=MUTED,
                    va="center")

    # The node sits at the midpoint of the slab: that is the -0.5w term.
    ax.plot(values, mid, color=CURVE, linewidth=1.8, zorder=3)
    ax.plot(values, mid, "o", color=CURVE, markersize=6, zorder=4)

    ax.axhline(Q, color=ACCENT, linewidth=1.2, linestyle="--", zorder=5)
    ax.plot([result, result], [0, Q], color=ACCENT, linewidth=1.2,
            linestyle="--", zorder=5)
    ax.plot([result], [Q], "o", color=ACCENT, markersize=7, zorder=6)
    ax.annotate(f"weighted median = {result:g}", (result, Q), xytext=(12, -26),
                textcoords="offset points", fontsize=9.5, color=ACCENT,
                fontweight="bold")
    ax.annotate("q = 0.5", (DATA[0] - 0.35, Q), xytext=(0, 6),
                textcoords="offset points", fontsize=8.5, color=ACCENT)

    style(ax)
    ax.set_xlim(DATA[0] - 0.6, DATA[-1] + 0.9)
    ax.set_ylim(0, 1.02)
    # Same padding as the right panel, so the two x labels line up.
    ax.set_xlabel("value", color=MUTED, fontsize=9.5, labelpad=24)
    ax.set_ylabel("cumulative probability", color=MUTED, fontsize=9.5)
    ax.set_title("Each value owns a slab of probability as tall as its weight.\n"
                 "The curve joins the slab midpoints.",
                 fontsize=10.5, color=INK, loc="left", pad=12)


def panel_comparison(ax):
    values, w, lower, upper, mid = weighted_ecdf(DATA, WEIGHTS)
    ours = wquantiles.quantile_1D(DATA, WEIGHTS, Q)
    # The discrete definition: the first value whose cumulative weight reaches q.
    theirs = values[np.searchsorted(upper, Q)]

    ax.plot(values, mid, color=CURVE, linewidth=1.8, zorder=4,
            label="this library — interpolated")
    ax.plot(values, mid, "o", color=CURVE, markersize=5, zorder=5)

    # The step function the discrete definition inverts.
    xs, ys = [values[0]], [0.0]
    for x, hi in zip(values, upper):
        xs += [x, x]
        ys += [ys[-1], hi]
    xs.append(values[-1] + 0.9)
    ys.append(ys[-1])
    ax.plot(xs, ys, color=DISCRETE, linewidth=1.6, zorder=3,
            label='numpy — method="inverted_cdf"')

    ax.axhline(Q, color=ACCENT, linewidth=1.1, linestyle="--", zorder=2)
    for x, colour in ((ours, CURVE), (theirs, DISCRETE)):
        ax.plot([x, x], [0, Q], color=colour, linewidth=1.1,
                linestyle=":", zorder=2)
        ax.plot([x], [0], "^", color=colour, markersize=8, clip_on=False, zorder=6)
    ax.annotate(f"{ours:g}", (ours, 0), xytext=(-6, -22), textcoords="offset points",
                fontsize=9.5, color=CURVE, fontweight="bold")
    ax.annotate(f"{theirs:g}", (theirs, 0), xytext=(-4, -22), textcoords="offset points",
                fontsize=9.5, color=DISCRETE, fontweight="bold")

    style(ax)
    ax.set_xlim(DATA[0] - 0.6, DATA[-1] + 0.9)
    ax.set_ylim(0, 1.02)
    # Extra padding: the two results are annotated below the axis line.
    ax.set_xlabel("value", color=MUTED, fontsize=9.5, labelpad=24)
    ax.set_title("The same data, two definitions.\n"
                 "The discrete one can only return a value that is in the data.",
                 fontsize=10.5, color=INK, loc="left", pad=12)
    legend = ax.legend(loc="lower right", fontsize=8.5, frameon=True,
                       facecolor="white", edgecolor=GRID)
    for text in legend.get_texts():
        text.set_color(MUTED)


def main():
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4), facecolor="white")
    panel_construction(axes[0])
    panel_comparison(axes[1])
    fig.suptitle(
        f"weighted median of {list(map(int, DATA))} with weights {list(map(int, WEIGHTS))}",
        fontsize=9, color=MUTED, y=0.995, x=0.007, ha="left",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    for suffix in ("svg", "png"):
        out = HERE / "figures" / f"weighted-median.{suffix}"
        fig.savefig(out, dpi=180, facecolor="white")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()

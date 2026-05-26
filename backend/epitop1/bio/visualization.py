"""
Visualization module for B-cell linear epitope prediction.

Plots score curves along the protein sequence, highlights predicted
epitope regions, and provides interactive hover tooltips showing
residue index, amino acid, and score values.

Requires **matplotlib**.  Falls back gracefully when matplotlib
is not installed.

Usage::

    from bio.visualization import plot_epitope_scores
    fig = plot_epitope_scores(residue_results, epitope_hits, title="MyProtein")
    fig.savefig("epitope_plot.png", dpi=150)

References
----------
Pellequer JL & Westhof E (1993) Methods Enzymol 237:1-11.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend by default
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:  # pragma: no cover
    HAS_MPL = False

from bio.scoring import ResidueResult
from bio.epitope_detector import EpitopeHit


# ── Colour palette ──────────────────────────────────────────────────────────

_COLOURS = {
    "combined":       "#2E86AB",
    "hydrophilicity": "#28A745",
    "accessibility":  "#FFC107",
    "flexibility":    "#DC3545",
    "beta_turn":      "#6F42C1",
    "antigenicity":   "#FD7E14",
    "epitope_fill":   "#2E86AB",
}


# ── Public API ──────────────────────────────────────────────────────────────

def plot_epitope_scores(
    residue_results: Sequence[ResidueResult],
    epitope_hits: Sequence[EpitopeHit] | None = None,
    title: str = "B-cell Linear Epitope Prediction",
    show_individual: bool = True,
    figsize: tuple[float, float] = (14, 7),
) -> "Figure":
    """Create a multi-panel epitope prediction plot.

    Parameters
    ----------
    residue_results : Sequence[ResidueResult]
        Per-residue score profile from :class:`CombinedScorer`.
    epitope_hits : Sequence[EpitopeHit] | None
        Detected epitope candidates (optional).
    title : str
        Plot title.
    show_individual : bool
        Whether to show individual predictor curves.
    figsize : tuple[float, float]
        Figure size (width, height) in inches.

    Returns
    -------
    matplotlib.figure.Figure

    Raises
    ------
    ImportError
        If matplotlib is not installed.
    """
    if not HAS_MPL:
        raise ImportError(
            "matplotlib is required for visualization.  "
            "Install it with:  pip install matplotlib"
        )

    n = len(residue_results)
    positions = np.arange(1, n + 1)

    combined = np.array([r.combined_score for r in residue_results])
    hydro = np.array([r.hydrophilicity for r in residue_results])
    access = np.array([r.accessibility for r in residue_results])
    flex = np.array([r.flexibility for r in residue_results])
    turn = np.array([r.beta_turn for r in residue_results])
    antig = np.array([r.antigenicity for r in residue_results])

    n_panels = 2 if show_individual else 1
    fig, axes = plt.subplots(
        n_panels, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [2, 1] if show_individual else [1]},
    )
    if n_panels == 1:
        axes = [axes]

    ax_main: plt.Axes = axes[0]  # type: ignore[assignment]

    # ---- Panel 1: Combined score + epitope highlights ----
    ax_main.plot(
        positions, combined,
        color=_COLOURS["combined"], linewidth=1.4, label="Combined score",
    )
    ax_main.fill_between(
        positions, 0, combined,
        color=_COLOURS["combined"], alpha=0.12,
    )

    # Highlight predicted epitopes
    if epitope_hits:
        for hit in epitope_hits:
            x0 = hit.start - 0.5
            width = hit.length
            rect = Rectangle(
                (x0, 0), width, 1.0,
                linewidth=0, facecolor=_COLOURS["epitope_fill"],
                alpha=0.18,
            )
            ax_main.add_patch(rect)
            # Label
            mid = hit.start + hit.length / 2
            ax_main.text(
                mid, combined[hit.start - 1:hit.end].max() + 0.03,
                f"#{hit.rank}",
                ha="center", va="bottom", fontsize=7, fontweight="bold",
                color=_COLOURS["epitope_fill"],
            )

    ax_main.set_ylabel("Combined Score", fontsize=10, fontweight="bold")
    ax_main.set_ylim(-0.02, 1.08)
    ax_main.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax_main.legend(loc="upper right", fontsize=8)
    ax_main.grid(axis="y", alpha=0.25)

    # ---- Panel 2: Individual profiles (normalised for visual comparison) ----
    if show_individual and n_panels > 1:
        ax_ind: plt.Axes = axes[1]  # type: ignore[assignment]
        lw = 0.9
        ax_ind.plot(positions, _norm(hydro), color=_COLOURS["hydrophilicity"],
                    lw=lw, label="Hydrophilicity")
        ax_ind.plot(positions, _norm(access), color=_COLOURS["accessibility"],
                    lw=lw, label="Accessibility")
        ax_ind.plot(positions, _norm(flex), color=_COLOURS["flexibility"],
                    lw=lw, label="Flexibility")
        ax_ind.plot(positions, _norm(turn), color=_COLOURS["beta_turn"],
                    lw=lw, label="Beta-turn")
        ax_ind.plot(positions, _norm(antig), color=_COLOURS["antigenicity"],
                    lw=lw, label="Antigenicity")

        ax_ind.set_ylabel("Normalised Score", fontsize=9)
        ax_ind.legend(loc="upper right", fontsize=7, ncol=3)
        ax_ind.set_ylim(-0.05, 1.10)
        ax_ind.grid(axis="y", alpha=0.25)

    axes[-1].set_xlabel("Residue Position", fontsize=10, fontweight="bold")
    axes[-1].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # ---- Interactive hover annotation (works in interactive backends) ----
    annot = ax_main.annotate(
        "", xy=(0, 0), xytext=(15, 15),
        textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFFFDD", alpha=0.92),
        fontsize=8,
    )
    annot.set_visible(False)

    def _on_hover(event):
        if event.inaxes != ax_main:
            annot.set_visible(False)
            fig.canvas.draw_idle()
            return
        x = event.xdata
        if x is None:
            return
        idx = int(round(x)) - 1
        if 0 <= idx < n:
            r = residue_results[idx]
            annot.xy = (idx + 1, combined[idx])
            text = (
                f"Pos {r.position} ({r.amino_acid})\n"
                f"Combined: {r.combined_score:.3f}\n"
                f"Hydro: {r.hydrophilicity:.2f}\n"
                f"Access: {r.accessibility:.2f}\n"
                f"Flex: {r.flexibility:.3f}\n"
                f"Turn: {r.beta_turn:.3f}\n"
                f"Antig: {r.antigenicity:.3f}"
            )
            annot.set_text(text)
            annot.set_visible(True)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", _on_hover)

    fig.tight_layout()
    return fig


def save_plot(
    residue_results: Sequence[ResidueResult],
    epitope_hits: Sequence[EpitopeHit] | None = None,
    filepath: str = "epitope_plot.png",
    title: str = "B-cell Linear Epitope Prediction",
    dpi: int = 150,
    **kwargs,
) -> str:
    """Render and save the epitope plot to a file.

    Parameters
    ----------
    filepath : str
        Destination image path (.png, .pdf, .svg supported).
    dpi : int
        Resolution in dots per inch.
    **kwargs
        Forwarded to :func:`plot_epitope_scores`.

    Returns
    -------
    str
        Path to the saved file.
    """
    fig = plot_epitope_scores(
        residue_results, epitope_hits, title=title, **kwargs,
    )
    fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return filepath


# ── Helpers ─────────────────────────────────────────────────────────────────

def _norm(arr: np.ndarray) -> np.ndarray:
    """Quick min-max normalisation for visual display."""
    mn, mx = np.min(arr), np.max(arr)
    if mx - mn < 1e-10:
        return np.full_like(arr, 0.5)
    return (arr - mn) / (mx - mn)

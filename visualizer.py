"""
visualizer.py: Generates publication-ready plots for titration analysis in GranTED.

Supports titration curve (pH vs volume) and Gran/Schwartz 3-panel subplots.
Saves PNGs to output_dir (300 DPI); optional BytesIO buffer for PDF embedding.

Dependencies: matplotlib, seaborn, numpy, pandas, pathlib.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO  # For buffer export


def setup_plot_style():
    """Set global Matplotlib/Seaborn style for consistent aesthetics."""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    plt.rc('font', size=10)
    plt.rc('axes', titlesize=12, labelsize=10)


def _get_labels(titration_type: str) -> Dict[str, str]:
    """Dynamic labels/titles based on titration_type."""
    labels = {
        'strong_acid': {'title': 'Strong Acid + Strong Base', 'ylabel': 'g1 (Pre-Equiv.)', 'region': 'Pre-Equivalence'},
        'weak_acid': {'title': 'Weak Acid + Strong Base', 'ylabel': 'g1 (Buffer Region)', 'region': 'Pre-Equivalence Approx.'},
        'strong_base': {'title': 'Strong Base + Strong Acid', 'ylabel': 'g1 (Post-Equiv.)', 'region': 'Post-Equivalence'},
        'weak_base': {'title': 'Weak Base + Strong Acid', 'ylabel': 'g1 (Buffer Region)', 'region': 'Post-Equivalence Approx.'}
    }
    if titration_type not in labels:
        return {'title': 'Titration Plot', 'ylabel': 'g1', 'region': 'Linear Zone'}
    return labels[titration_type]


def plot_titration_curve(df: pd.DataFrame, params: Dict[str, Any], output_dir: Path,
                         embed_in_pdf: bool = False) -> Optional[BytesIO]:
    """Plot simplified titration curve: pH vs. volume (black line with points, no overlays)."""
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    labels = _get_labels(titration_type)

    fig, ax = plt.subplots(figsize=(8, 5))
    pH = 7.0 - df['potential'] / 59.16  # Nernst conversion

    # Direct plot on ax (no _create_subplots for single—avoids overlay)
    ax.plot(df['volume'], pH, 'k-o', linewidth=1.5, markersize=4, label='pH')  # Black line with circles
    ax.set_xlabel('Titrant Volume (mL)')
    ax.set_ylabel('pH')
    ax.set_title(f"Titration Curve: {labels['title']}")
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)  # Light grid for readability

    # Tight limits to data (no padding/duplication)
    ax.set_xlim(min(df['volume']) - 1, max(df['volume']) + 1)
    ax.set_ylim(min(pH) - 0.2, max(pH) + 0.2)

    fig.tight_layout(pad=1.5)  # Space cleanly, no bleed

    filename = output_dir / 'titration_curve.png'
    if embed_in_pdf:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        print(f"Curve buffer ready for PDF (embed mode).")
        return buf
    else:
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved titration curve to {filename}.")
        return None


def plot_gran_functions_combined(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: Path, embed_in_pdf: bool = False) -> Optional[BytesIO]:
    """
    3-panel combined plot for Gran/Schwartz comparison (shared x-axis).
    Top: Gran g1 + fit/opt zone. Middle: Schwartz gs + fit/opt zone.
    Bottom: Negative derivative (Gran opt zone shaded).
    Linear y-axis for all panels.
    """
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    labels = _get_labels(titration_type)
    volume = df['volume'].values

    # Extract from results (fallbacks for flat baseline structure)
    g1 = results.get('g1', np.zeros(len(volume)))  # Raw Gran
    gs = results.get('g1_opt', np.zeros(len(volume)))  # Opt Schwartz gs (assume 'g1_opt' for Schwartz)
    raw_zone_start = results.get('raw_zone', {}).get('start', 0)
    raw_zone_end = results.get('raw_zone', {}).get('end', len(volume))
    opt_zone_start = results.get('opt_zone', {}).get('start', 0)
    opt_zone_end = results.get('opt_zone', {}).get('end', len(volume))
    raw_fit = results.get('raw_zone', {}).get('fit', (0, 0))  # (slope, intercept) tuple
    opt_fit = results.get('opt_zone', {}).get('fit', (0, 0))  # (slope, intercept) tuple

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 10), sharex=True, gridspec_kw={'hspace': 0.3})

    # Top: Gran g1 + fit/opt zone (linear y)
    ax1.plot(volume, g1, 'b-', linewidth=1.5, label='Gran g1')
    if gran_opt_zone[0] is not None:
        start_v, end_v = volume[gran_opt_zone[0]], volume[gran_opt_zone[1]]
        ax1.axvspan(start_v, end_v, alpha=0.3, color='yellow', label='Opt Zone')
    if gran_fit:
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = gran_fit['slope'] * x_fit + gran_fit['intercept']
        ax1.plot(x_fit, y_fit, 'r--', label=f'Fit (R²={gran_fit["rvalue"]**2:.3f})')
    ax1.set_ylabel('Gran g1')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Middle: Schwartz gs + fit/opt zone (linear y)
    ax2.plot(volume, gs, 'g-', linewidth=1.5, label='Schwartz gs')
    if schwartz_opt_zone[0] is not None:
        start_v, end_v = volume[schwartz_opt_zone[0]], volume[schwartz_opt_zone[1]]
        ax2.axvspan(start_v, end_v, alpha=0.3, color='lightblue', label='Opt Zone')
    if schwartz_fit:
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = schwartz_fit['slope'] * x_fit + schwartz_fit['intercept']
        ax2.plot(x_fit, y_fit, 'orange', linestyle='--', label=f'Fit (R²={schwartz_fit["rvalue"]**2:.3f})')
    ax2.set_ylabel('Schwartz gs')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Bottom: Negative derivative (Gran opt zone shaded)
    deriv = np.gradient(g1, volume)  # Use Gran g1 for deriv
    neg_deriv = deriv[deriv < 0]  # Filter negative region
    neg_vol = volume[deriv < 0]  # Corresponding volumes
    ax3.plot(neg_vol, neg_deriv, 'purple', linewidth=1.5, label='Negative d g1 / dv')
    if gran_opt_zone[0] is not None:
        # Shade Gran opt zone on negative deriv (filter to neg only)
        neg_mask = (neg_vol >= volume[gran_opt_zone[0]]) & (neg_vol <= volume[gran_opt_zone[1]])
        if np.any(neg_mask):
            start_v_neg = neg_vol[neg_mask][0] if neg_mask.any() else volume[gran_opt_zone[0]]
            end_v_neg = neg_vol[neg_mask][-1] if neg_mask.any() else volume[gran_opt_zone[1]]
            ax3.axvspan(start_v_neg, end_v_neg, alpha=0.3, color='yellow', label='Gran Opt Zone')
    ax3.set_xlabel('Titrant Volume (mL)')
    ax3.set_ylabel('d g1 / dv (negative)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    fig.suptitle(f"Gran/Schwartz Analysis: {labels['title']}", fontsize=14, y=0.98)
    fig.tight_layout()

    filename = output_dir / 'gran_functions.png'
    if embed_in_pdf:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        print(f"Combined gran_functions buffer ready for PDF.")
        return buf
    else:
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved combined gran_functions plot to {filename}.")
        return None

def visualize_all(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any],
                  output_dir: str = '.', embed_in_pdf: bool = False) -> Dict[str, Optional[BytesIO]]:
    """
    Orchestrate all plots: curve and gran/schwartz subplots.
    Returns dict of buffers if embed=True, else saves PNGs.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    buffers = {}  # For PDF embed
    titration_type = params.get('titration_type', 'weak_acid')
    pH = results.get('pH', 7.0 - df['potential'] / 59.16)
    volume = df['volume'].values

    # Curve (always)
    buf_curve = plot_titration_curve(df, params, output_dir, embed_in_pdf)
    if embed_in_pdf:
        buffers['curve'] = buf_curve

    # Combined subplots (Gran/Schwartz + deriv)
    buf_combined = plot_gran_functions_combined(df, params, results, output_dir, embed_in_pdf)
    if embed_in_pdf:
        buffers['gran_functions'] = buf_combined

    if not embed_in_pdf:
        print("All PNG visualizations saved to output_dir.")
    else:
        print("All plot buffers ready for PDF embedding.")
    return buffers


if __name__ == "__main__":
    # Standalone test (mock data/results)
    df = pd.DataFrame({'volume': np.linspace(0, 30, 20), 'potential': np.linspace(0, -200, 20)})
    params = {'titration_type': 'weak_acid', 'V': 25.0}
    results = {'gran': {'g1': np.random.rand(20)}, 'schwartz': {'gs': np.random.rand(20)}, 'pH': np.random.rand(20)}
    visualize_all(df, params, results, output_dir='./test_plots')
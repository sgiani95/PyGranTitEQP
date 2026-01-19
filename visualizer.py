"""
visualizer.py: Generates publication-ready plots for titration analysis in GranTED.

Supports titration curve, Gran/Schwartz functions (raw/opt with zones), and derivatives.
Saves PNGs to output_dir (300 DPI); optional BytesIO buffer for PDF embedding.
Dynamic for both methods; fallbacks for raw-only mode.

Dependencies: matplotlib, seaborn, numpy, pandas, scipy, pathlib.
Local: gran_functions (for recompute fallback).
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import savgol_filter
from typing import Dict, Any, Optional, Tuple
from io import BytesIO  # For buffer export

from gran_functions import compute_gran_functions  # Fallback recompute


def setup_plot_style():
    """Set global Matplotlib/Seaborn style for consistent aesthetics."""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    plt.rc('font', size=10)
    plt.rc('axes', titlesize=12, labelsize=10)


def _create_subplots(fig: plt.Figure, df: pd.DataFrame, pH: np.ndarray, method: str,
                     titration_type: str, num_subplots: int = 3) -> Tuple[plt.Axes, ...]:
    """Helper: Create and populate subplots for curve (1), raw g (2), opt g (3)."""
    gs = fig.add_gridspec(num_subplots, 1, hspace=0.3, height_ratios=[1, 1, 1] if num_subplots == 3 else [1])

    # Subplot 1: Titration curve (volume vs. potential/pH)
    ax1 = fig.add_subplot(gs[0])
    ax1_twin = ax1.twinx()
    ax1.plot(df['volume'], df['potential'], 'b-', label='Potential (mV)', linewidth=1.5)
    ax1_twin.plot(df['volume'], pH, 'r--', label='pH', linewidth=1.5)
    ax1.set_xlabel('Titrant Volume (mL)')
    ax1.set_ylabel('Potential (mV)', color='b')
    ax1_twin.set_ylabel('pH', color='r')
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')

    if num_subplots == 1:
        return (ax1,)
    elif num_subplots == 3:
        # Subplot 2: Raw g vs. volume
        ax2 = fig.add_subplot(gs[1])
        ax2.set_xlabel('Titrant Volume (mL)')
        ax2.set_ylabel('g1/gs (Raw)')

        # Subplot 3: Optimized g
        ax3 = fig.add_subplot(gs[2])
        ax3.set_xlabel('Titrant Volume (mL)')
        ax3.set_ylabel('g1/gs (Optimized)')

        return ax1, ax2, ax3
    else:
        raise ValueError(f"Unsupported num_subplots: {num_subplots}. Use 1 or 3.")


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
    """Plot titration curve with pH secondary axis."""
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    labels = _get_labels(titration_type)

    fig, ax = plt.subplots(figsize=(8, 5))
    pH = 7.0 - df['potential'] / 59.16  # Inline Nernst (fallback)

    # Use _create_subplots for consistency (1 subplot)
    ax1, = _create_subplots(fig, df, pH, 'curve', titration_type, num_subplots=1)
    ax1.set_title(f"Titration Curve: {labels['title']}")

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


def plot_gran_functions(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any],
                        method: str, output_dir: Path, embed_in_pdf: bool = False) -> Optional[BytesIO]:
    """3-subplot Gran/Schwartz plot: curve, raw g, opt g with zone/fit."""
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    labels = _get_labels(titration_type)
    ylabel = 'gs' if method == 'schwartz' else labels['ylabel']

    # Fallback: Recompute if no results
    if method not in results:
        print(f"No {method} in results; recomputing raw.")
        raw_results = compute_gran_functions(df, params)
        g_raw = raw_results[method]['g1' if method == 'gran' else 'gs']
        pH = raw_results['pH']
        volume = df['volume'].values
    else:
        g_raw = results[method].get('g1' if method == 'gran' else 'gs', np.zeros(len(df)))
        pH = results.get('pH', 7.0 - df['potential'] / 59.16)
        volume = df['volume'].values

    # Optimized: Fallback to raw if no zones/fits
    zones = results.get(method, {}).get('zones')  # Tuple (start_idx, end_idx)
    fit = results.get(method, {}).get('fit')  # Dict {slope, intercept, rvalue}
    optimized_k = results.get(method, {}).get('optimized_k', 0.0)
    opt_g = g_raw  # Default to raw
    if zones and fit:
        # Recompute opt g with k (stub—use lambda if available)
        lambda_func = results[method].get('gran_func')
        if callable(lambda_func):
            opt_g = lambda_func(volume, pH, optimized_k)
        print(f"Plotted optimized {method} with k={optimized_k}, zone {zones}, R²={fit.get('rvalue', 'N/A')**2:.3f}.")
    else:
        print(f"No zones/fit for {method}; plotting raw only.")

    fig = plt.figure(figsize=(8, 10))
    ax1, ax2, ax3 = _create_subplots(fig, df, pH, method, titration_type, num_subplots=3)

    # Subplot 1: Curve (already populated)
    ax1.set_title(f"{method.capitalize()} Plot: {labels['title']} ({labels['region']})")

    # Subplot 2: Raw g
    ax2.plot(volume, g_raw, 'g-', label='Raw g1/gs', linewidth=1.5)
    ax2.set_yscale('log')  # Common for Gran
    ax2.legend()

    # Subplot 3: Opt g + zone/fit
    ax3.plot(volume, opt_g, 'm-', label='Optimized g1/gs', linewidth=1.5)
    if zones:
        zone_start, zone_end = volume[zones[0]], volume[zones[1]]
        ax3.axvspan(zone_start, zone_end, alpha=0.3, color='yellow', label='Linear Zone')
    if fit:
        x_fit = np.array([volume.min(), volume.max()])
        y_fit = fit['slope'] * x_fit + fit['intercept']
        ax3.plot(x_fit, y_fit, 'r--', label=f'Fit (R²={fit["rvalue"]**2:.3f})')
    ax3.set_yscale('log')  # Common for Gran
    ax3.legend()

    filename = output_dir / f'{method}_plot.png'
    if embed_in_pdf:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        print(f"{method} buffer ready for PDF.")
        return buf
    else:
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved {method} plot to {filename}.")
        return None


def plot_derivatives(volume: np.ndarray, g_values: np.ndarray, zones: Optional[Tuple[int, int]],
                     output_dir: Path, method: str = 'gran', embed_in_pdf: bool = False) -> Optional[BytesIO]:
    """Plot g vs. volume + derivative (dg/dv) with zone shading on deriv."""
    setup_plot_style()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), height_ratios=[1, 1], sharex=True)

    # Top: g line
    ax1.plot(volume, g_values, 'b-', linewidth=1.5)
    ax1.set_ylabel('g1/gs')
    ax1.set_title(f'{method.capitalize()} Derivatives')

    # Bottom: Smoothed derivative
    if len(g_values) < 5:
        deriv = np.gradient(g_values, volume)
    else:
        smoothed_g = savgol_filter(g_values, window_length=5, polyorder=2)
        deriv = np.gradient(smoothed_g, volume)
    colors = ['red' if d > 0 else 'blue' for d in deriv]  # Simple color by sign
    ax2.scatter(volume, deriv, c=colors, s=20, cmap='RdYlBu')
    ax2.set_ylabel('dg/dv')
    ax2.set_xlabel('Titrant Volume (mL)')

    # Zone shade on deriv (if provided)
    if zones:
        zone_start, zone_end = volume[zones[0]], volume[zones[1]]
        ax2.axvspan(zone_start, zone_end, alpha=0.3, color='green', label='Flat Zone (Low |dg/dv|)')
        ax2.legend()

    filename = output_dir / f'{method}_derivatives.png'
    if embed_in_pdf:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        print(f"{method} derivatives buffer ready.")
        return buf
    else:
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved {method} derivatives to {filename}.")
        return None


def visualize_all(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any],
                  output_dir: str = '.', embed_in_pdf: bool = False) -> Dict[str, Optional[BytesIO]]:
    """
    Orchestrate all plots: curve, methods (gran/schwartz), derivatives.
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

    # Dynamic methods
    methods = ['gran', 'schwartz'] if 'schwartz' in results else ['gran']
    for method in methods:
        buf_method = plot_gran_functions(df, params, results, method, output_dir, embed_in_pdf)
        if embed_in_pdf:
            buffers[method] = buf_method

        # Derivatives per method
        g_vals = results[method].get('g1' if method == 'gran' else 'gs')
        zones = results.get(method, {}).get('zones')
        buf_deriv = plot_derivatives(volume, g_vals, zones, output_dir, method, embed_in_pdf)
        if embed_in_pdf:
            buffers[f'{method}_derivatives'] = buf_deriv

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
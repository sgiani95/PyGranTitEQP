"""
visualizer.py: Generates publication-ready plots for GranTED titration analysis.
Creates:
- titration_curve.png: pH vs volume (simple black line with points)
- gran_schwartz.png: 3-panel comparison (Gran raw/opt, Schwartz opt, negative derivative)
- k_screening.png: optional screening plot (if 'g1_screened' in results)

Saves high-res PNGs (300 DPI) to output_dir.
Dependencies: matplotlib, seaborn, numpy, pandas, pathlib, scipy.signal.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from scipy.signal import savgol_filter


def setup_plot_style():
    """Set consistent professional style."""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    plt.rc('font', size=10)
    plt.rc('axes', titlesize=12, labelsize=10)


def _get_labels(titration_type: str = 'weak_acid') -> Dict[str, str]:
    """
    Returns the same title and ylabel for all cases (no type-specific differences).
    """
    return {
        'title': 'Titration Analysis',
        'ylabel': 'g1'
    }


def plot_titration_curve(df: pd.DataFrame, params: Dict[str, Any], output_dir: Path = Path('output')):
    """
    Plot simple titration curve: pH vs volume (black line with points).
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    volume = df['volume'].to_numpy()
    potential = df['potential'].to_numpy()
    pH = 7.0 - potential / 59.16

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(volume, pH, 'k-o', linewidth=1.2, markersize=4, label='Titration Curve (pH)')
    ax.set_xlabel('Titrant Volume (mL)')
    ax.set_ylabel('pH')
    ax.set_title('Titration Curve')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    filename = output_dir / 'titration_curve.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Titration curve saved to {filename}")


def plot_gran_schwartz(results: Dict[str, Any], params: Dict[str, Any], output_dir: Path = Path('output')):
    """
    3-panel plot with line-point style:
    1. Gran raw g1 ('b-o') + raw fit dashed line + raw zone shade
    2. Schwartz optimized gs ('g-o') + opt fit dashed line + opt zone shade
    3. Negative derivative from raw g1 with opt zone shade

    Panel titles include V_eq (and k for Schwartz opt).
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    volume = params.get('volume_array', np.arange(41))  # Fallback

    # ──────────────────────────────────────────────
    # Safe extraction from nested results
    # ──────────────────────────────────────────────
    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    g1_raw = results.get('g1', np.zeros(len(volume)))
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))  # gs_opt

    # Zones with fallback
    raw_zone_start = gran_raw.get('zone_start', 0)
    raw_zone_end = gran_raw.get('zone_end', len(volume) - 1)
    opt_zone_start = sch_opt.get('zone_start', raw_zone_start)
    opt_zone_end = sch_opt.get('zone_end', raw_zone_end)

    # Fits and r2 (separate keys)
    raw_fit = gran_raw.get('fit', None)  # (slope, intercept)
    raw_r2 = gran_raw.get('r2', 'N/A')
    opt_fit = sch_opt.get('fit', None)
    opt_r2 = sch_opt.get('r2', 'N/A')
    opt_k5 = sch_opt.get('k5', 0.0)

    # Debug print to confirm fit is present
    print(f"DEBUG: raw_fit = {raw_fit}, raw_r2 = {raw_r2}")
    print(f"DEBUG: opt_fit = {opt_fit}, opt_r2 = {opt_r2}, k5 = {opt_k5}")

    # ──────────────────────────────────────────────
    # Figure
    # ──────────────────────────────────────────────
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # Panel 1: Gran raw g1 + fit + zone
    ax1.plot(volume, g1_raw, 'b-o', linewidth=1.5, markersize=4, label='Gran raw g1')
    ax1.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='red', label='Raw Zone')

    if raw_fit:
        slope, intercept = raw_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax1.plot(x_fit, y_fit, 'k--', label=f'Raw fit (R²={raw_r2:.4f})')
    else:
        print("DEBUG: No raw fit available — skipping dashed line")

    ax1.set_ylabel('Gran g1 (raw)')
    ax1.set_title(f'Gran Raw – V_eq = {gran_raw.get("V_eq", "N/A"):.3f} mL')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Panel 2: Schwartz optimized gs + fit + zone
    ax2.plot(volume, gs_opt, 'g-o', linewidth=1.5, markersize=4, label='Schwartz opt gs')
    ax2.axvspan(volume[opt_zone_start], volume[opt_zone_end], alpha=0.25, color='orange', label='Opt Zone')

    if opt_fit:
        slope, intercept = opt_fit
        y_fit = slope * x_fit + intercept
        ax2.plot(x_fit, y_fit, 'k--', label=f'Opt fit (R²={opt_r2:.4f})')
    else:
        print("DEBUG: No opt fit available — skipping dashed line")

    ax2.set_ylabel('Schwartz gs (opt)')
    ax2.set_title(f'Schwartz Optimized – V_eq = {sch_opt.get("V_eq", "N/A"):.3f} mL, k = {opt_k5:.3f}')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: Negative derivative
    deriv = np.gradient(g1_raw, volume)
    neg_mask = deriv < 0
    if np.any(neg_mask):
        neg_vol = volume[neg_mask]
        neg_deriv = deriv[neg_mask]
        ax3.plot(neg_vol, neg_deriv, 'purple', linewidth=1.5, label='Negative d g1 / dv')

        zone_neg_mask = (neg_vol >= volume[opt_zone_start]) & (neg_vol <= volume[opt_zone_end])
        if np.any(zone_neg_mask):
            neg_vol_zone = neg_vol[zone_neg_mask]
            ax3.axvspan(neg_vol_zone[0], neg_vol_zone[-1], alpha=0.3, color='yellow', label='Opt Zone')
    else:
        ax3.text(0.5, 0.5, 'No negative derivative', ha='center', va='center', transform=ax3.transAxes)

    ax3.axhline(0, color='gray', linestyle='--', label='Zero')
    ax3.set_xlabel('Titrant Volume (mL)')
    ax3.set_ylabel('d g1 / dv (negative)')
    ax3.set_title('Negative Derivative (raw g1)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    fig.suptitle('Gran/Schwartz Analysis', fontsize=14)
    fig.tight_layout()
    filename = output_dir / 'gran_schwartz.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Gran/Schwartz combined plot saved to {filename}")

def visualize_all(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: str = 'output'):
    """
    Orchestrate all plots: titration curve + gran/schwartz combined.
    """
    output_dir = Path(output_dir)
    plot_titration_curve(df, params, output_dir)
    plot_gran_schwartz(results, params, output_dir)
    print(f"All visualizations saved to {output_dir}")
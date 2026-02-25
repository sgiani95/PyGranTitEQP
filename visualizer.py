"""
visualizer.py: Generates publication-ready plots for GranTED titration analysis.
Creates:
- titration_curve.png: pH vs volume (simple black line with points)
- gran_schwartz.png: 3-panel comparison (Gran raw/opt, Schwartz opt, negative derivative)
- k_screening.png: optional screening plot (if 'g1_screened' in results)

- Gran diagnostic plot: “how R² behaved as we moved/stabilized the right boundary”
- Schwartz diagnostic plot: “how R² improved as we extended the left boundary”

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
    3. Negative derivative from raw g1 with **RAW zone** shaded (changed from opt)
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    volume = params.get('volume_array', np.arange(41))  # Fallback

    # Safe extraction from nested results
    gran_raw = results.get('gran', {}).get('raw', {})
    gran_opt = results.get('gran', {}).get('opt', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    g1_raw = results.get('g1', np.zeros(len(volume)))
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))  # gs_opt

    # Zones
    raw_zone_start = gran_raw.get('zone_start', 0)
    raw_zone_end = gran_raw.get('zone_end', len(volume) - 1)
    opt_zone_start = sch_opt.get('zone_start', raw_zone_start)
    opt_zone_end = sch_opt.get('zone_end', raw_zone_end)

    # Fits and r2
    raw_fit = gran_raw.get('fit', None)
    raw_r2 = gran_raw.get('r2', 'N/A')
    opt_fit = sch_opt.get('fit', None)
    opt_r2 = sch_opt.get('r2', 'N/A')
    opt_k5 = sch_opt.get('k5', 0.0)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # Panel 1: Gran raw g1 + fit + zone
    ax1.plot(volume, g1_raw, 'b-o', linewidth=1.5, markersize=4, label='Gran raw g1')
    ax1.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='red', label='Raw Zone')
    if raw_fit:
        slope, intercept = raw_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax1.plot(x_fit, y_fit, 'k--', label=f'Raw fit (R²={raw_r2:.4f})')
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
    ax2.set_ylabel('Schwartz gs (opt)')
    opt_k = sch_opt.get('k', 0.0)
    ax2.set_title(f'Schwartz Optimized – V_eq = {sch_opt.get("V_eq", "N/A"):.3f} mL, k = {opt_k:.3f}')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: Negative derivative (from raw g1) with **RAW zone** shaded
    deriv = np.gradient(g1_raw, volume)
    neg_mask = deriv < 0

    if np.any(neg_mask):
        neg_vol = volume[neg_mask]
        neg_deriv = deriv[neg_mask]
        ax3.plot(neg_vol, neg_deriv, 'purple', linewidth=1.5, label='Negative d g1 / dv')

        # Shade **RAW zone** on negative deriv (changed from opt)
        zone_neg_mask = (neg_vol >= volume[raw_zone_start]) & (neg_vol <= volume[raw_zone_end])
        if np.any(zone_neg_mask):
            neg_vol_zone = neg_vol[zone_neg_mask]
            ax3.axvspan(neg_vol_zone[0], neg_vol_zone[-1], alpha=0.3, color='red', label='Raw Zone')
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

def plot_all_combined(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: Path = Path('output')):
    """
    Combined vertical plot saved as 'plots.png':
    - Top: Titration curve (pH vs volume)
    - Middle: Gran raw g1 + fit + raw zone shade
    - Bottom: Schwartz optimized gs + fit + opt zone shade
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    volume = df['volume'].values
    potential = df['potential'].values
    pH = 7.0 - potential / 59.16

    # Extract Gran/Schwartz data
    g1_raw = results.get('g1', np.zeros(len(volume)))
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))

    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    raw_zone_start = gran_raw.get('zone_start', 0)
    raw_zone_end = gran_raw.get('zone_end', len(volume) - 1)
    opt_zone_start = sch_opt.get('zone_start', raw_zone_start)
    opt_zone_end = sch_opt.get('zone_end', raw_zone_end)

    raw_fit = gran_raw.get('fit', None)
    opt_fit = sch_opt.get('fit', None)

    opt_k5 = sch_opt.get('k5', 0.0)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15), sharex=True)

    # Top: Titration curve
    ax1.plot(volume, pH, 'k-o', linewidth=1.5, markersize=4, label='Titration Curve (pH)')
    ax1.set_ylabel('pH')
    ax1.set_title('Titration Curve')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Middle: Gran raw g1 + fit + zone
    ax2.plot(volume, g1_raw, 'b-o', linewidth=1.5, markersize=4, label='Gran raw g1')
    ax2.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='red', label='Raw Zone')
    if raw_fit:
        slope, intercept = raw_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax2.plot(x_fit, y_fit, 'k--', label=f'Raw fit (R²={gran_raw.get("r2", "N/A"):.4f})')
    ax2.set_ylabel('Gran g1 (raw)')
    ax2.set_title(f'Gran Raw – V_eq = {gran_raw.get("V_eq", "N/A"):.3f} mL')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Bottom: Schwartz optimized gs + fit + zone
    ax3.plot(volume, gs_opt, 'g-o', linewidth=1.5, markersize=4, label='Schwartz opt gs')
    ax3.axvspan(volume[opt_zone_start], volume[opt_zone_end], alpha=0.25, color='orange', label='Opt Zone')
    if opt_fit:
        slope, intercept = opt_fit
        y_fit = slope * x_fit + intercept
        ax3.plot(x_fit, y_fit, 'k--', label=f'Opt fit (R²={sch_opt.get("r2", "N/A"):.4f})')
    ax3.set_ylabel('Schwartz gs (opt)')
    opt_k = sch_opt.get('k', 0.0)  # Use the renamed 'k' from metrics
    ax3.set_title(f'Schwartz Optimized – V_eq = {sch_opt.get("V_eq", "N/A"):.3f} mL, k = {opt_k:.3f}')
    ax3.set_xlabel('Titrant Volume (mL)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    fig.suptitle('GranTED Analysis Overview', fontsize=16)
    fig.tight_layout()
    filename = output_dir / 'plots.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Combined overview plot saved to {filename}")

def plot_r2_vs_upper_bound(r2_vs_upper: list[tuple[float, float]], output_dir: Path = Path('output')):
    """
    Plot R2 at every trial step as function of the upper bound volume (raw Gran scouting).
    """
    if not r2_vs_upper:
        print("No R2 history available for plotting.")
        return

    upper_volumes, r2_values = zip(*r2_vs_upper)  # Unpack list of tuples

    plt.figure(figsize=(8, 6))
    plt.plot(upper_volumes, r2_values, 'b-o', linewidth=1.5, markersize=4, label='Candidate R2')
    plt.xlabel('Upper Bound Volume (mL)')
    plt.ylabel('R2')
    plt.title('R2 vs Upper Bound Volume (Raw Gran Trial Search)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    filename = output_dir / 'r2_vs_upper_bound.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"R2 vs upper bound plot saved to {filename}")

def plot_diagnostics(
    results: Dict[str, Any],
    params: Dict[str, Any],
    output_dir: Path = Path('output')
) -> None:
    """
    Creates a two-panel diagnostic plot:
      - Upper: Initial Gran search → R² vs upper bound of tested intervals (sorted)
      - Lower: Optimized Schwartz search → R² vs lower bound of tested intervals (sorted)
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    # ─── Extract diagnostic data ───
    init_diag = results.get('initial_gran_diagnostics', {})
    opt_diag  = results.get('opt_schwartz_diagnostics', {})

    if not init_diag.get('R2_values') or not opt_diag.get('R2_values'):
        print("Warning: No diagnostic data available for R² search plots.")
        return

    # Volume array (needed to locate selected bounds)
    volume = params.get('volume_array', np.arange(41))  # fallback consistent with other plots

    # ─── Gran (initial, raw, k=0) ───
    v_upper_init = np.array(init_diag.get('V_upper_ml', []))
    r2_init      = np.array(init_diag.get('R2_values', []))

    # Sort by upper volume → much smoother curve
    if len(v_upper_init) > 0:
        sort_idx_init = np.argsort(v_upper_init)
        sorted_v_upper_init = v_upper_init[sort_idx_init]
        sorted_r2_init      = r2_init[sort_idx_init]
    else:
        sorted_v_upper_init = np.array([])
        sorted_r2_init      = np.array([])

    # Selected upper bound (from the final raw zone)
    raw_zone = results.get('raw_zone', {})  # or results['gran']['raw'] if nested
    selected_upper = volume[raw_zone.get('zone_end', 0)] if 'zone_end' in raw_zone else None

    # ─── Schwartz (optimized) ───
    v_lower_opt = np.array(opt_diag.get('V_lower_ml', []))
    r2_opt      = np.array(opt_diag.get('R2_values', []))

    # Sort by lower volume → smooth curve
    if len(v_lower_opt) > 0:
        sort_idx_opt = np.argsort(v_lower_opt)
        sorted_v_lower_opt = v_lower_opt[sort_idx_opt]
        sorted_r2_opt      = r2_opt[sort_idx_opt]
    else:
        sorted_v_lower_opt = np.array([])
        sorted_r2_opt      = np.array([])

    # Selected lower bound (from the final optimized zone)
    opt_zone = results.get('opt_zone', {})  # or results['schwartz']['opt']
    selected_lower = volume[opt_zone.get('zone_start', 0)] if 'zone_start' in opt_zone else None

    # ─── Create figure ───
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=False)

    # Upper panel – Initial Gran
    if len(sorted_v_upper_init) > 0:
        ax1.plot(sorted_v_upper_init, sorted_r2_init, 'b-o',
                 linewidth=1.5, markersize=4, alpha=0.8,
                 label='Candidates (sorted by upper volume)')
        if selected_upper is not None:
            ax1.axvline(selected_upper, color='red', ls='--', lw=1.8,
                        label='Selected upper bound')
    ax1.set_title('Initial Gran search (k=0) – R² vs right boundary')
    ax1.set_xlabel('Upper bound of tested interval [mL]')
    ax1.set_ylabel('R²')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Lower panel – Optimized Schwartz
    if len(sorted_v_lower_opt) > 0:
        ax2.plot(sorted_v_lower_opt, sorted_r2_opt, 'g-o',
                 linewidth=1.5, markersize=4, alpha=0.8,
                 label='Candidates (sorted by lower volume)')
        if selected_lower is not None:
            ax2.axvline(selected_lower, color='red', ls='--', lw=1.8,
                        label='Selected lower bound')
    ax2.set_title('Optimized Schwartz search – R² vs left boundary')
    ax2.set_xlabel('Lower bound of tested interval [mL]')
    ax2.set_ylabel('R²')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.suptitle('Linear Region Search Diagnostics', fontsize=14)
    fig.tight_layout()

    filename = output_dir / 'search_diagnostics_sorted.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"Search diagnostics plot (sorted by volume) saved to {filename}")

def visualize_all(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: str = 'output'):
    output_dir = Path(output_dir)
    plot_titration_curve(df, params, output_dir)
    plot_gran_schwartz(results, params, output_dir)
    plot_all_combined(df, params, results, output_dir)
    plot_diagnostics(results, params, output_dir)

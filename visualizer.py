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
    """Professional style"""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    
    # Larger fonts for better readability in double-column papers
    plt.rc('font', size=13)
    plt.rc('axes', titlesize=15, labelsize=14)
    plt.rc('xtick', labelsize=12)
    plt.rc('ytick', labelsize=12)
    plt.rc('legend', fontsize=12)
    
    # Thicker outer frame (spines)
    plt.rc('axes', linewidth=1.6)
    plt.rc('patch', linewidth=1.2)
    
    # Grid style
    plt.rc('grid', alpha=0.3, linewidth=0.8)

def _get_labels(titration_type: str = 'weak_acid') -> Dict[str, str]:
    """
    Returns the same title and ylabel for all cases (no type-specific differences).
    """
    return {
        'title': 'Titration Analysis',
        'ylabel': 'g1'
    }


def plot_titration_curve(
    df: pd.DataFrame,
    params: Dict[str, Any],
    output_dir: Path = Path('output'),
    potential_original: np.ndarray | None = None
):
    """
    Plot simple titration curve: pH vs volume (black line with points).
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    volume = df['volume'].to_numpy()
    potential_plot = df.get('potential_original', df['potential']).values
    pH = 7.0 - potential_plot / 59.16

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
    #ax1.plot(volume, g1_raw, 'b-o', linewidth=1.5, markersize=4, label='Gran raw g1')
    #ax1.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='red', label='Raw Zone')
    ax1.plot(volume, g1_raw, color='C0', marker='o', linewidth=1.5, markersize=4, label='Gran raw g1')
    ax1.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='C0', label='Raw Zone')
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
    #     ax2.plot(volume, gs_opt, color='C1', marker='s', linewidth=2.5, markersize=7, markerfacecolor='white', markeredgecolor='C1', label='Schwartz opt gs')
    ax2.plot(volume, gs_opt, color='C1', marker='o', linewidth=1.5, markersize=4, label='Schwartz opt gs')
    ax2.axvspan(volume[opt_zone_start], volume[opt_zone_end], alpha=0.25, color='C1', label='Opt Zone')
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
        ax3.plot(neg_vol, neg_deriv, 'C4', linewidth=1.5, label='Negative d g1 / dv')

        # Shade **RAW zone** on negative deriv (changed from opt)
        zone_neg_mask = (neg_vol >= volume[raw_zone_start]) & (neg_vol <= volume[raw_zone_end])
        if np.any(zone_neg_mask):
            neg_vol_zone = neg_vol[zone_neg_mask]
            ax3.axvspan(neg_vol_zone[0], neg_vol_zone[-1], alpha=0.3, color='C0', label='Raw Zone')
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

def plot_all_combined(
    df: pd.DataFrame,
    params: Dict[str, Any],
    results: Dict[str, Any],
    output_dir: Path = Path('output'),
    potential_original: np.ndarray | None = None
):
    """
    Combined vertical plot saved as 'plots.png':
    - Top: Titration curve (pH vs volume)
    - Bottom: Schwartz optimized gs + fit + opt zone shade
    (Middle Gran raw g1 panel removed)
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)
    volume = df['volume'].values
    potential_plot = df.get('potential_original', df['potential']).values
    pH = 7.0 - potential_plot / 59.16

    # Extract Schwartz data
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))
    sch_opt = results.get('schwartz', {}).get('opt', {})
    opt_zone_start = sch_opt.get('zone_start', 0)
    opt_zone_end = sch_opt.get('zone_end', len(volume) - 1)
    opt_fit = sch_opt.get('fit', None)
    opt_r2 = sch_opt.get('r2', 'N/A')
    opt_veq = sch_opt.get('V_eq', 'N/A')
    opt_k = sch_opt.get('k', 0.0)

    # Only two panels now
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)

    # Top: Titration curve (unchanged)
    ax1.plot(volume, pH, 'k-o', linewidth=1.5, markersize=4, label='Titration Curve (pH)')
    ax1.set_ylabel('pH')
    ax1.set_title('\nTitration Curve\n')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Bottom: Schwartz optimized gs + fit + zone (moved from old bottom)
    ax2.plot(volume, gs_opt, color='C1', marker='o', linewidth=1.5, markersize=4, label='Opt Schwartz gs')
    ax2.axvspan(volume[opt_zone_start], volume[opt_zone_end], alpha=0.25, color='C1', label='Opt Zone')
    if opt_fit:
        slope, intercept = opt_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax2.plot(x_fit, y_fit, 'k--', label=f'Opt fit (R²={opt_r2:.4f})')
    # ax2.axvline(opt_veq, color='green', ls='-', lw=1.5, label=f'V_eq = {opt_veq:.3f} mL')
    ax2.set_ylabel('Opt Schwartz gs')
    ax2.set_title(f'\nOpt Schwartz EQP = {opt_veq:.3f} mL, k = {opt_k:.3f}\n')
    ax2.set_xlabel('Titrant Volume (mL)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ### ax1.set_ylim(2.5, 10.5)
    ### ax2.set_xlim(-0.25, 6.75)
    ### ax2.set_ylim(-0.0000010, 0.000013)

    fig.suptitle('GranTED Analysis Overview', fontsize=16)
    fig.tight_layout()
    filename = output_dir / 'plots.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    ###
    base_name = output_dir / 'plots'
    fig.savefig(base_name.with_suffix('.pdf'), bbox_inches='tight')   # Best for LaTeX
    ###
    plt.close(fig)

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

def plot_gran_raw_with_search_diagnostic(results: Dict[str, Any], params: Dict[str, Any], output_dir: Path = Path('output')):
    """
    2-panel plot with line-point style:
    1. Upper: Gran raw g1 ('b-o') + raw fit dashed line + raw zone shade (exact same as original upper panel)
    2. Lower: Initial Gran linear region search (R² vs upper volume bound, sorted)
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)
    volume = params.get('volume_array', np.arange(41)) # Fallback

    # Safe extraction from nested results
    gran_raw = results.get('gran', {}).get('raw', {})
    g1_raw = results.get('g1', np.zeros(len(volume)))
    raw_zone_start = gran_raw.get('zone_start', 0)
    raw_zone_end = gran_raw.get('zone_end', len(volume) - 1)
    raw_fit = gran_raw.get('fit', None)
    raw_r2 = gran_raw.get('r2', 'N/A')
    raw_veq = gran_raw.get('V_eq', 'N/A')

    # ─── Diagnostic data for lower panel ───
    init_diag = results.get('initial_gran_diagnostics', {})
    v_upper = np.array(init_diag.get('V_upper_ml', []))
    r2_vals = np.array(init_diag.get('R2_values', []))
    selected_upper = volume[raw_zone_end] if raw_zone_end < len(volume) else None

    # Sort by upper volume for smooth curve
    if len(v_upper) > 0:
        sort_idx = np.argsort(v_upper)
        v_upper = v_upper[sort_idx]
        r2_vals = r2_vals[sort_idx]

    # ─── Figure ───
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=False, height_ratios=[2, 1])

    # ─── Upper panel: exact same as original Gran raw ───
    ax1.plot(volume, g1_raw, 'b-o', linewidth=1.5, markersize=4, label='Gran raw g1')
    ax1.axvspan(volume[raw_zone_start], volume[raw_zone_end], alpha=0.25, color='red', label='Raw Zone')
    if raw_fit:
        slope, intercept = raw_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax1.plot(x_fit, y_fit, 'k--', label=f'Raw fit (R²={raw_r2:.4f})')
    ax1.axvline(raw_veq, color='green', ls='-', lw=1.5, label=f'V_eq = {raw_veq:.3f} mL')
    ax1.set_ylabel('Gran g1 (raw)')
    ax1.set_title(f'Gran Raw – V_eq = {raw_veq:.3f} mL')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # ─── Lower panel: Initial Gran search diagnostic ───
    if len(v_upper) > 0:
        ax2.plot(v_upper, r2_vals, 'b-o', linewidth=1.5, markersize=4, label='Candidates (sorted)')
        if selected_upper is not None:
            ax2.axvline(selected_upper, color='red', ls='--', lw=1.8, label='Selected upper bound')
    else:
        ax2.text(0.5, 0.5, 'No diagnostic data', ha='center', va='center', transform=ax2.transAxes)

    ax2.set_title('Initial Gran linear region search')
    ax2.set_xlabel('Upper bound of tested interval [mL]')
    ax2.set_ylabel('R²')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.suptitle('Gran Analysis + Linear Region Search', fontsize=14)
    fig.tight_layout()
    filename = output_dir / 'gran_raw_with_search_diagnostic.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_schwartz_opt_with_search_diagnostic(
    results: Dict[str, Any],
    params: Dict[str, Any],
    output_dir: Path = Path('output')
) -> None:
    """
    Two-panel plot for Schwartz Optimized:
      - Upper: Schwartz opt gs ('g-o') + opt fit dashed line + opt zone shade (exact same as original Schwartz panel)
      - Lower: Optimized Schwartz linear region search (R² vs lower volume bound, sorted)
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)
    volume = params.get('volume_array', np.arange(41))  # fallback

    # Safe extraction
    sch_opt = results.get('schwartz', {}).get('opt', {})
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))  # gs_opt
    opt_zone_start = sch_opt.get('zone_start', 0)
    opt_zone_end = sch_opt.get('zone_end', len(volume) - 1)
    opt_fit = sch_opt.get('fit', None)
    opt_r2 = sch_opt.get('r2', 'N/A')
    opt_veq = sch_opt.get('V_eq', 'N/A')
    opt_k = sch_opt.get('k', 0.0)

    # ─── Diagnostic data for lower panel ───
    opt_diag = results.get('opt_schwartz_diagnostics', {})
    if not opt_diag.get('R2_values'):
        print("Warning: No optimized Schwartz diagnostics available → skipping lower panel.")
        v_lower = r2_vals = np.array([])
        selected_lower = None
    else:
        v_lower = np.array(opt_diag.get('V_lower_ml', []))
        r2_vals = np.array(opt_diag.get('R2_values', []))
        # Sort by lower volume (ascending)
        if len(v_lower) > 0:
            sort_idx = np.argsort(v_lower)
            v_lower = v_lower[sort_idx]
            r2_vals = r2_vals[sort_idx]
        selected_lower = volume[opt_zone_start] if opt_zone_start < len(volume) else None

    # ─── Figure ───
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=False, height_ratios=[2, 1])

    # ─── Upper panel: exact same as original Schwartz optimized ───
    ax1.plot(volume, gs_opt, 'g-o', linewidth=1.5, markersize=4, label='Schwartz opt gs')
    ax1.axvspan(volume[opt_zone_start], volume[opt_zone_end], alpha=0.25, color='orange', label='Opt Zone')
    if opt_fit:
        slope, intercept = opt_fit
        x_fit = np.linspace(volume.min(), volume.max(), 100)
        y_fit = slope * x_fit + intercept
        ax1.plot(x_fit, y_fit, 'k--', label=f'Opt fit (R²={opt_r2:.4f})')
    ax1.axvline(opt_veq, color='green', ls='-', lw=1.5, label=f'V_eq = {opt_veq:.3f} mL')
    ax1.set_ylabel('Schwartz gs (opt)')
    ax1.set_title(f'Schwartz Optimized – V_eq = {opt_veq:.3f} mL, k = {opt_k:.3f}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # ─── Lower panel: Optimized Schwartz search diagnostic ───
    if len(v_lower) > 0:
        ax2.plot(v_lower, r2_vals, 'g-o', linewidth=1.5, markersize=4, label='Candidates (sorted by lower bound)')
        if selected_lower is not None:
            ax2.axvline(selected_lower, color='red', ls='--', lw=1.8, label='Selected lower bound')
    else:
        ax2.text(0.5, 0.5, 'No diagnostic data', ha='center', va='center', transform=ax2.transAxes)

    ax2.set_title('Optimized Schwartz linear region search')
    ax2.set_xlabel('Lower bound of tested interval [mL]')
    ax2.set_ylabel('R²')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.suptitle('Schwartz Optimized + Linear Region Search Diagnostic', fontsize=14)
    fig.tight_layout()

    filename = output_dir / 'schwartz_opt_with_search_diagnostic.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_development_summary(
    collected: Dict[str, list],
    output_dir: Path,
    full_volume: np.ndarray | None = None,
    earliest_n: int | None = None,
    reference_veq: float | None = None,
    r2_min: float = 0.99,
    unc_max: float = 0.05,
    veq_tolerance: float = 0.1
):
    """
    Summary plot with reversed insets:
    - Main panels: only data >= threshold (clean zoomed view)
    - Small insets: full dataset for context
    """
    setup_plot_style()
    output_dir.mkdir(exist_ok=True)

    max_volumes = np.array(collected['max_volume'])
    V_eq = np.array(collected['V_eq'])
    V_eq_unc = np.array(collected['V_eq_unc'])
    R2 = np.array(collected['R2'])

    # Calculate threshold volume (round down to nearest 0.5 mL)
    if earliest_n is not None and earliest_n in collected.get('n_points', []):
        idx = collected['n_points'].index(earliest_n)
        earliest_volume = collected['max_volume'][idx]
        threshold_volume = np.floor(earliest_volume * 2) / 2
        print(f"Threshold volume applied: {threshold_volume:.1f} mL (based on earliest {earliest_volume:.2f} mL)")
    else:
        threshold_volume = 0.0

    # Filter for main panels (zoomed / clean view)
    valid_zoomed = (max_volumes >= threshold_volume) & (~np.isnan(V_eq))

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # ====================== MAIN PANELS (ZOOMED / CLEAN) ======================
    # Top: V_eq
    ax1.errorbar(max_volumes[valid_zoomed], V_eq[valid_zoomed], yerr=V_eq_unc[valid_zoomed],
                 fmt='o-', capsize=5, color='C0', label='V_eq ± unc', zorder=3)
    ax1.plot(max_volumes[valid_zoomed], V_eq[valid_zoomed], '-', color='C0', alpha=0.5)

    if reference_veq is not None:
        ax1.set_ylim(reference_veq - 3 * veq_tolerance, reference_veq + 3 * veq_tolerance)
    ax1.set_ylabel('V_eq [mL]')
    ax1.set_title('Development mode: Convergence (relevant region only)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Middle: uncertainty
    ax2.plot(max_volumes[valid_zoomed], V_eq_unc[valid_zoomed], 'o-', color='C1', label='V_eq_unc')
    ax2.set_ylim(0.0, 3 * unc_max)
    ax2.set_ylabel('Uncertainty [mL]')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Bottom: R²
    ax3.plot(max_volumes[valid_zoomed], R2[valid_zoomed], 'o-', color='C2', label='R²')
    ax3.set_ylim(1 - 3 * (1 - r2_min), 1.0)
    ax3.set_xlabel('Maximum titrant volume used [mL]')
    ax3.set_ylabel('R²')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # Mark earliest acceptable point
    if earliest_n is not None and earliest_n in collected.get('n_points', []):
        idx = collected['n_points'].index(earliest_n)
        earliest_volume = collected['max_volume'][idx]
        for ax in (ax1, ax2, ax3):
            ax.axvline(earliest_volume, color='red', ls='--', lw=1.8,
                       label=f'EAV (vol = {earliest_volume:.3f} mL)')
        ax1.legend()

    # ====================== INSETS (FULL DATASET) ======================
    # Create small inset in the upper-right of each panel showing the FULL data
    for ax, data, label, color in [
        (ax1, V_eq, 'V_eq full', 'C0'),
        (ax2, V_eq_unc, 'Unc full', 'C1'),
        (ax3, R2, 'R² full', 'C2')
    ]:
        inset = ax.inset_axes([0.125, 0.125, 0.50, 0.75])
        inset.plot(max_volumes, data, 'o-', color=color, markersize=2, alpha=0.7, label=label)
        # inset.set_title('Full dataset', fontsize=8)
        inset.grid(True, alpha=0.3)
        inset.tick_params(labelsize=10)

        # Light red vertical line in inset too
        if earliest_n is not None and earliest_n in collected.get('n_points', []):
            inset.axvline(earliest_volume, color='red', ls='--', lw=1.0, alpha=0.8)

    ax3.scatter([0], [1.0], color='white', alpha=0.0, zorder=1)   # transparent ghost point
    plt.tight_layout()
    filename = output_dir / 'development_convergence_volume.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Development summary plot saved: {filename}")

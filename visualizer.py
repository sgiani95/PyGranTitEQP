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

def dump_data_for_debug(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: Path = Path('output')):
    """
    Dump data for debugging:
    - volume vs pH (from df['potential'])
    - volume vs gran function (raw g1)
    - volume vs schwartz function (optimized gs / g1_opt)
    
    Saves 3 separate tab-separated text files in output_dir/debug_dump/
    """
    debug_dir = output_dir / 'debug_dump'
    debug_dir.mkdir(exist_ok=True)

    volume = df['volume'].values

    # 1. volume vs pH
    potential = df['potential'].values
    pH = 7.0 - potential / 59.16
    pH_file = debug_dir / 'volume_vs_pH.txt'
    with open(pH_file, 'w', encoding='utf-8') as f:
        f.write("volume\tpH\n")
        for v, ph in zip(volume, pH):
            f.write(f"{v:.6f}\t{ph:.6f}\n")
    print(f"Dumped volume vs pH to {pH_file}")

    # 2. volume vs gran raw (g1)
    g1_raw = results.get('g1', np.zeros(len(volume)))
    gran_file = debug_dir / 'volume_vs_gran_raw.txt'
    with open(gran_file, 'w', encoding='utf-8') as f:
        f.write("volume\tgran_raw_g1\n")
        for v, g in zip(volume, g1_raw):
            f.write(f"{v:.6f}\t{g:.6f}\n")
    print(f"Dumped volume vs gran_raw_g1 to {gran_file}")

    # 3. volume vs schwartz optimized (gs_opt / g1_opt)
    gs_opt = results.get('g1_opt', np.zeros(len(volume)))
    schwartz_file = debug_dir / 'volume_vs_schwartz_opt.txt'
    with open(schwartz_file, 'w', encoding='utf-8') as f:
        f.write("volume\tschwartz_opt_gs\n")
        for v, gs in zip(volume, gs_opt):
            f.write(f"{v:.6f}\t{gs:.6f}\n")
    print(f"Dumped volume vs schwartz_opt_gs to {schwartz_file}")
    
def visualize_all(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: str = 'output'):
    output_dir = Path(output_dir)
    plot_titration_curve(df, params, output_dir)
    plot_gran_schwartz(results, params, output_dir)  # Keep if you want both
    plot_all_combined(df, params, results, output_dir)  # New combined vertical plot
    print(f"All visualizations saved to {output_dir}")
    dump_data_for_debug(df, params, results, output_dir)
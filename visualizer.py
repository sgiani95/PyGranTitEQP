"""
visualizer.py: Generates publication-ready plots for titration curves, Gran/Schwartz functions, and derivatives.

Minimal changes: titration_curve.png shows pH vs. volume only.
gran_plot.png: 3 panels (Gran g1 + fit/zone, Schwartz gs + fit/zone, negative first derivative).
Grey background via 'darkgrid' style. Preserves original structure where possible.

Dependencies: matplotlib, seaborn, numpy, pandas, scipy, pathlib.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import savgol_filter
from scipy.stats import linregress  # For interpolation if needed


def setup_plot_style():
    """Set global Matplotlib/Seaborn style for consistency (grey background)."""
    sns.set_style('darkgrid')  # Grey background restored
    sns.set_context('paper')
    sns.set_palette('deep')
    plt.rc('font', size=10)


def plot_titration_curve(df, params, output_dir='.'):
    """Plot pH vs. volume only (modified for pH focus)."""
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    
    volume = df['volume'].values
    potential = df['potential'].values
    pH = 7.0 - potential / 59.16  # Compute pH
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(volume, pH, 'b-', linewidth=1.5, marker='o', markersize=4)
    ax.set_xlabel('Titrant Volume (mL)')
    ax.set_ylabel('pH')
    ax.set_title(f'Titration Curve (pH vs. Volume) - {titration_type}')
    
    output_path = Path(output_dir) / 'titration_curve.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved titration curve (pH vs. volume) to {output_path}")


def plot_gran_functions(df, params, results, output_dir='.'):
    """3-panel plot: Top Gran g1 + fit/zone, Middle Schwartz gs + fit/zone, Bottom negative first derivative."""
    setup_plot_style()
    titration_type = params.get('titration_type', 'weak_acid')
    
    volume = df['volume'].values
    potential = df['potential'].values
    pH = results.get('pH', 7.0 - potential / 59.16)
    
    # Extract from results (fallback to raw compute if missing)
    if 'gran' not in results or 'schwartz' not in results:
        from gran_functions import compute_gran_functions
        raw_results = compute_gran_functions(df, params)
        g1 = raw_results['gran']['g1']
        gran_func = raw_results['gran']['gran_func']
        gs = raw_results['schwartz']['gs']
        schwartz_func = raw_results['schwartz']['gran_func']
        # Default zones/fits (placeholder; assume from analyzer later)
        gran_zones = (5, 15)  # Mock for now
        schwartz_zones = (6, 16)
        # Mock fits (linregress on zone)
        gran_fit = linregress(volume[gran_zones[0]:gran_zones[1]], g1[gran_zones[0]:gran_zones[1]])
        schwartz_fit = linregress(volume[schwartz_zones[0]:schwartz_zones[1]], gs[schwartz_zones[0]:schwartz_zones[1]])
    else:
        g1 = results['gran']['g1']
        gran_func = results['gran']['gran_func']
        gs = results['schwartz']['gs']
        schwartz_func = results['schwartz']['gran_func']
        gran_zones = results['gran'].get('zones', (5, 15))
        schwartz_zones = results['schwartz'].get('zones', (6, 16))
        gran_fit = results['gran'].get('fit', linregress(volume[gran_zones[0]:gran_zones[1]], g1[gran_zones[0]:gran_zones[1]]))
        schwartz_fit = results['schwartz'].get('fit', linregress(volume[schwartz_zones[0]:schwartz_zones[1]], gs[schwartz_zones[0]:schwartz_zones[1]]))
    
    # Optimized k fallback
    optimized_k = 0.0  # From analyzer later
    g1_opt = gran_func(volume, pH, optimized_k)
    gs_opt = schwartz_func(volume, pH, optimized_k)
    
    fig, axs = plt.subplots(3, 1, figsize=(8, 12))
    
    # Top: Gran g1 + linear interpolation (fit) + zone
    axs[0].plot(volume, g1_opt, 'g-', linewidth=1.5, label='Gran g1')
    axs[0].set_ylabel('Gran g1')
    axs[0].set_title(f'Gran Function - {titration_type}')
    axs[0].legend()
    # Zone shade
    axs[0].axvspan(gran_zones[0], gran_zones[1], alpha=0.3, color='yellow', label='Zone')
    # Linear fit (interpolation)
    x_fit = np.linspace(gran_zones[0], gran_zones[1], 100)
    y_fit = gran_fit.slope * x_fit + gran_fit.intercept
    axs[0].plot(x_fit, y_fit, 'r--', label=f'Linear Fit (R²={gran_fit.rvalue**2:.3f})')
    axs[0].legend()
    
    # Middle: Schwartz gs + linear interpolation + zone
    axs[1].plot(volume, gs_opt, 'm-', linewidth=1.5, label='Schwartz gs')
    axs[1].set_ylabel('Schwartz gs')
    axs[1].set_title(f'Schwartz Function - {titration_type}')
    axs[1].legend()
    # Zone shade
    axs[1].axvspan(schwartz_zones[0], schwartz_zones[1], alpha=0.3, color='yellow', label='Zone')
    # Linear fit
    y_fit_s = schwartz_fit.slope * x_fit + schwartz_fit.intercept
    axs[1].plot(x_fit, y_fit_s, 'r--', label=f'Linear Fit (R²={schwartz_fit.rvalue**2:.3f})')
    axs[1].legend()
    
    # Bottom: Negative part of first derivative (from Gran g1 for simplicity)
    dg_dv = -np.gradient(g1_opt, volume)  # Negative first derivative
    if len(volume) >= 5:
        dg_dv_smooth = savgol_filter(dg_dv, window_length=5, polyorder=2)
    else:
        dg_dv_smooth = dg_dv
    axs[2].plot(volume, dg_dv_smooth, 'k-', linewidth=1.5)
    axs[2].set_ylabel('-dg/dv')
    axs[2].set_xlabel('Titrant Volume (mL)')
    axs[2].set_title('Negative First Derivative')
    # Shade zones on deriv if present (combined)
    combined_zone_start, combined_zone_end = min(gran_zones[0], schwartz_zones[0]), max(gran_zones[1], schwartz_zones[1])
    axs[2].axvspan(combined_zone_start, combined_zone_end, alpha=0.3, color='green', label='Combined Zone')
    axs[2].legend()
    
    plt.tight_layout()
    
    output_path = Path(output_dir) / 'gran_plot.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved 3-panel gran plot to {output_path}")


def visualize_all(df, params, results, output_dir='.'):
    """Orchestrate: titration curve + gran plot (combined)."""
    Path(output_dir).mkdir(exist_ok=True)
    
    plot_titration_curve(df, params, output_dir)
    plot_gran_functions(df, params, results, output_dir)
    
    print("All visualizations saved to", output_dir)


if __name__ == "__main__":
    # Quick test stub (mock inputs)
    import pandas as pd
    df = pd.DataFrame({'volume': np.linspace(0, 30, 20), 'potential': np.linspace(0, -200, 20)})
    params = {'titration_type': 'weak_acid', 'V': 25.0}
    # Mock results with basics
    results = {'pH': 7.0 - df['potential'].values / 59.16}  # Will fallback for others
    visualize_all(df, params, results, './test_output')

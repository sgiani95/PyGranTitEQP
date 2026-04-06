"""
Offline histogram plot optimized for double-column LaTeX.
Larger fonts and thicker frame.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path

def setup_plot_style():
    """Stronger style for LaTeX double-column"""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    
    # Larger fonts
    plt.rc('font', size=14)                    # base font
    plt.rc('axes', titlesize=16, labelsize=15)
    plt.rc('xtick', labelsize=13)
    plt.rc('ytick', labelsize=13)
    plt.rc('legend', fontsize=13)
    
    # Thicker outer frame (spines)
    plt.rc('axes', linewidth=1.5)
    plt.rc('patch', linewidth=1.2)

setup_plot_style()

# ====================== YOUR DATA ======================
deviations = ['0.010', '0.020', '0.050']

# TRIS/HCl
tris_values = [12.070, 14.078, 27.870]
tris_std    = [0.181,  0.264,  0.935]

# KHP/NaOH
khp_values = [10.803, 13.872, 36.832]
khp_std    = [0.050,  0.256,  0.515]

x = np.arange(len(deviations))
width = 0.35

fig, ax = plt.subplots(figsize=(7.5, 5.8))   # Good size for one column in double-column LaTeX

# Bars
bars1 = ax.bar(x - width/2, tris_values, width, yerr=tris_std, 
               capsize=6, label='TRIS/HCl', color='#1f77b4', alpha=0.3, linewidth=1.2)
bars2 = ax.bar(x + width/2, khp_values, width, yerr=khp_std, 
               capsize=6, label='KHP/NaOH', color='#ff7f0e', alpha=0.3, linewidth=1.2)

# Labels and title
ax.set_xlabel('\nMaximum Allowed Deviation from EQP* (mL)', labelpad=10)
ax.set_ylabel('Reagent Saved (%)\n', labelpad=10)
ax.set_title('Reagent Savings Compared to Conventional Method (100%)\n', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(deviations)
ax.set_ylim(0.0, 40)

ax.legend(loc='upper left', frameon=True, fancybox=True, edgecolor='gray', framealpha=0.5)
ax.grid(True, alpha=0.3, linewidth=0.8)

# Value labels on top of bars
def add_value_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 9),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='medium')

add_value_labels(bars1)
add_value_labels(bars2)

# Thicker outer frame
for spine in ax.spines.values():
    spine.set_linewidth(1.6)

plt.tight_layout()

# Save high-resolution versions
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

fig.savefig(output_dir / 'deviation_histogram.png', dpi=400, bbox_inches='tight')
fig.savefig(output_dir / 'deviation_histogram.pdf', bbox_inches='tight')   # Recommended for LaTeX

print("Plots saved:")
print("   → output/deviation_histogram.png")
print("   → output/deviation_histogram.pdf  (best for LaTeX)")

plt.show()

"""
Offline histogram plot matching GranTED style.
Shows % values with error bars for TRIS/HCl and KHP/NaOH.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path

def setup_plot_style():
    """Same style as GranTED"""
    sns.set_style('whitegrid')
    sns.set_context('paper')
    plt.rc('font', size=14)
    plt.rc('axes', titlesize=14, labelsize=14)
    plt.rc('xtick', labelsize=14)
    plt.rc('ytick', labelsize=14)
    plt.rc('legend', fontsize=14)

setup_plot_style()

# ====================== YOUR DATA ======================
deviations = ['0.01', '0.02', '0.05']   # x-axis labels

# TRIS/HCl
tris_values = [12.070, 14.078, 27.870]
tris_std    = [0.181,  0.264,  0.935]

# KHP/NaOH
khp_values = [10.803, 13.872, 36.832]
khp_std    = [0.050,  0.256,  0.515]

x = np.arange(len(deviations))      # [0, 1, 2]
width = 0.35                        # width of the bars

fig, ax = plt.subplots(figsize=(9, 6))

# Bars
bars1 = ax.bar(x - width/2, tris_values, width, yerr=tris_std, 
               capsize=5, label='TRIS/HCl', color='#1f77b4', alpha=0.9)
bars2 = ax.bar(x + width/2, khp_values, width, yerr=khp_std, 
               capsize=5, label='KHP/NaOH', color='#ff7f0e', alpha=0.9)

# Labels and title
ax.set_xlabel('\nMaximum Allowed Deviation from EQP (mL)')
ax.set_ylabel('Percentage (%)\n')
ax.set_title('Solvent Saving\n')
ax.set_xticks(x)
ax.set_xticklabels(deviations)
ax.set_ylim(0, 40)


ax.legend(loc='upper left')
ax.grid(True, alpha=0.3)

# Add value labels on top of bars (optional but nice)
def add_value_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 8),  # 8 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12)

add_value_labels(bars1)
add_value_labels(bars2)

plt.tight_layout()

# Save
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)
filename = output_dir / 'deviation_histogram.png'
fig.savefig(filename, dpi=300, bbox_inches='tight')
plt.show()

print(f"Plot saved as: {filename}")

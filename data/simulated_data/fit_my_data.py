# fit_my_data.py
import pandas as pd
from titration_hh_fit import fit_hh, plot_fit

# Load your experimental file (adjust path and format)
df = pd.read_csv('data.dat', sep=r'\s+', header=None, names=['volume', 'potential'])

# Compute pH (use your exact method if different)
pH = 7.0 - df['potential'] / 59.16

volume = df['volume'].values
pH = pH.values

# Initial guess for V_eq — look at your curve or use derivative peak
V_eq_guess = 4.087 # CHANGE THIS to your estimate!

print("Fitting your data...")
popt, pcov = fit_hh(volume, pH, V_eq_guess=V_eq_guess)

if popt is not None:
    print("\nPlotting fit...")
    plot_fit(volume, pH, popt, V_eq_guess=V_eq_guess)
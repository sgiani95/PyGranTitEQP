"""
titration_hh_fit.py

Standalone module to fit an experimental acid-base titration curve
using the Henderson-Hasselbalch equation in the buffer region.

Fits pKa, V_eq (equivalence volume), and offset.

Usage:
    python titration_hh_fit.py   # runs example on synthetic data
    or import and use in your script:
        from titration_hh_fit import fit_hh, plot_fit
"""

import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def hh_buffer(V, pKa, V_eq, offset):
    """
    Henderson-Hasselbalch model for buffer region (V < V_eq)
    pH = pKa + log10( V / (V_eq - V) ) + offset
    """
    # Avoid log(0) or negative denominator
    ratio = V / (V_eq - V + 1e-10)
    ratio = np.clip(ratio, 1e-6, 1e6)  # prevent extreme values
    return pKa + np.log10(ratio) + offset


def fit_hh(volume, pH, V_eq_guess, pKa_guess=4.76, offset_guess=0.0,
           bounds=([0, 0, -5], [14, np.inf, 5])):
    """
    Fit Henderson-Hasselbalch to titration data (buffer region).

    Parameters:
        volume: array of added titrant volumes (mL)
        pH: array of measured pH
        V_eq_guess: initial guess for equivalence volume (mL)
        pKa_guess: initial guess for pKa (default 4.76 for acetic acid)
        offset_guess: initial guess for offset
        bounds: (min, max) for parameters [pKa, V_eq, offset]

    Returns:
        popt: optimized parameters [pKa, V_eq, offset]
        pcov: covariance matrix
    """
    # Use only points before equivalence (rough filter)
    mask = volume < V_eq_guess * 1.1  # a bit of margin
    x = volume[mask]
    y = pH[mask]

    p0 = [pKa_guess, V_eq_guess, offset_guess]

    try:
        popt, pcov = curve_fit(
            hh_buffer,
            x,
            y,
            p0=p0,
            bounds=bounds,
            maxfev=10000
        )
        print("Fit successful!")
        print(f"  pKa     = {popt[0]:.3f}")
        print(f"  V_eq    = {popt[1]:.3f} mL")
        print(f"  offset  = {popt[2]:.3f}")
        return popt, pcov
    except Exception as e:
        print("Fit failed:", e)
        return None, None


def plot_fit(volume, pH, popt, V_eq_guess=None):
    """
    Plot experimental data + fitted Henderson-Hasselbalch curve.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(volume, pH, 'o', label='Experimental data', alpha=0.7, color='C0')

    if popt is not None:
        V_fit = np.linspace(min(volume), max(volume), 300)
        pH_fit = hh_buffer(V_fit, *popt)
        plt.plot(V_fit, pH_fit, '-', label='HH fit', linewidth=2, color='C1')
        plt.axvline(popt[1], color='red', linestyle='--', 
                    label=f'V_eq = {popt[1]:.3f} mL')

    if V_eq_guess is not None:
        plt.axvline(V_eq_guess, color='gray', linestyle=':', 
                    label=f'Initial guess V_eq = {V_eq_guess:.1f} mL')

    plt.xlabel('Added titrant volume (mL)')
    plt.ylabel('pH')
    plt.title('Titration Curve Fit with Henderson-Hasselbalch')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


# Example usage (runs synthetic test when script is executed directly)
if __name__ == "__main__":
    # Synthetic data example (acetic acid titration)
    V_eq_true = 10.0
    pKa_true = 4.76
    offset_true = 0.1
    volume = np.linspace(0, 15, 80)
    true_pH = hh_buffer(volume, pKa_true, V_eq_true, offset_true) + np.random.normal(0, 0.03, len(volume))

    print("Fitting synthetic data...")
    popt, pcov = fit_hh(volume, true_pH, V_eq_guess=9.5)

    print("\nPlotting fit...")
    plot_fit(volume, true_pH, popt, V_eq_guess=9.5)
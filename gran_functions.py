"""
gran_functions.py: Mathematical core for computing Gran and Schwartz functions in acid-base titrations.

Computes g1 (Gran, 4 distinct types) and gs (Schwartz, 2 types) arrays; returns reusable Schwartz lambda (with k for analyzer.py).
pH conversion from potential (mV) via Nernst (25°C). k=0 fixed for arrays; lambdas tunable.
Assumes acid + strong base or base + strong acid. For weak Gran: v only (no V0); strong/Schwartz: V0 + v.

Dependencies: numpy, pandas.
"""

import numpy as np
import pandas as pd
from typing import Dict, Callable, Any


def compute_gran_functions(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute Gran and Schwartz g1/gs functions based on titration_type.

    Args:
        df: DataFrame with 'volume' (titrant vol, mL) and 'potential' (mV) columns.
        params: Dict with 'titration_type' (e.g., 'weak_acid' or 'acid'/'base' for Schwartz),
                'V' (initial vol, mL, default 25.0). Computes both methods by default.

    Returns:
        Dict with 'gran' (dict: 'g1' array and lambda), 'schwartz' (dict: 'gs' array and lambda for analyzer.py), 'pH' (array).

    Raises:
        ValueError: For unknown titration_type.
    """
    # Extract and coerce data
    volume = pd.to_numeric(df['volume'], errors='coerce').dropna().values
    potential = pd.to_numeric(df['potential'], errors='coerce').dropna().values
    if len(volume) != len(potential):
        raise ValueError("Volume and potential arrays must have equal length after cleaning.")

    # Nernst conversion to pH (25°C, E = -59.16 * (pH - 7) mV)
    pH = 7.0 - potential / 59.16

    V0 = params.get('V', 25.0)  # Initial volume
    titration_type = params.get('titration_type', 'weak_acid')

    k = 0.0  # Fixed for computation; lambda allows optimization

    results = {}

    # Gran: 4 distinct functions (weak: v only; strong: V0 + v)
    if titration_type == 'strong_acid':
        # Strong acid + strong base: g1 = (V0 + v) * 10^{-pH}
        gran_func = lambda v, ph, kk: (V0 + v) * np.power(10, -ph)  # Ignores kk (placeholder)
        g1 = gran_func(volume, pH, k)
        print(f"Gran strong_acid: g1 computed with k={k}.")
    elif titration_type == 'weak_acid':
        # Weak acid + strong base: g1 = v * 10^{k - pH} (V0 dropped for weak)
        gran_func = lambda v, ph, kk: v * np.power(10, kk - ph)
        g1 = gran_func(volume, pH, k)
        print(f"Gran weak_acid: g1 computed with k={k}.")
    elif titration_type == 'strong_base':
        # Strong base + strong acid: g1 = (V0 + v) * 10^{pH - 14}
        gran_func = lambda v, ph, kk: (V0 + v) * np.power(10, ph - 14)  # Ignores kk
        g1 = gran_func(volume, pH, k)
        print(f"Gran strong_base: g1 computed with k={k}.")
    elif titration_type == 'weak_base':
        # Weak base + strong acid: g1 = v * 10^{pH + k - 14} (V0 dropped for weak)
        gran_func = lambda v, ph, kk: v * np.power(10, ph + kk - 14)
        g1 = gran_func(volume, pH, k)
        print(f"Gran weak_base: g1 computed with k={k}.")
    else:
        raise ValueError(f"Unknown titration_type '{titration_type}'. Valid: strong_acid, weak_acid, strong_base, weak_base.")

    results['gran'] = {
        'g1': g1,
        'gran_func': gran_func  # Lambda for potential analyzer use (though Schwartz-focused)
    }

    # Schwartz: 2 types (weak-based, as extension; keep V0 + v)
    acid_mode = titration_type in ['strong_acid', 'weak_acid']
    if acid_mode:
        # Schwartz for acid (extension of weak acid; V' adjustment in analyzer)
        schwartz_func = lambda v, ph, kk: (V0 + v) * np.power(10, kk - ph)
        gs = schwartz_func(volume, pH, k)
        print(f"Schwartz acid: gs computed with k={k}.")
    else:
        # Schwartz for base (mirrored weak)
        schwartz_func = lambda v, ph, kk: (V0 + v) * np.power(10, ph + kk - 14)
        gs = schwartz_func(volume, pH, k)
        print(f"Schwartz base: gs computed with k={k}.")

    results['schwartz'] = {
        'gs': gs,
        'gran_func': schwartz_func  # Lambda for analyzer.py (Schwartz-specific)
    }

    # Add pH for downstream reuse
    results['pH'] = pH

    print("Gran and Schwartz functions computed successfully.")
    return results


if __name__ == "__main__":
    # Standalone test (requires sample df/params)
    import pandas as pd
    test_df = pd.DataFrame({
        'volume': np.linspace(0, 30, 10),
        'potential': np.linspace(0, -200, 10)  # Simulated drop in potential
    })
    test_params = {'titration_type': 'weak_acid', 'V': 25.0}
    results = compute_gran_functions(test_df, test_params)
    print(f"Gran g1 shape: {results['gran']['g1'].shape}, sample: {results['gran']['g1'][:3]}")
    print(f"Schwartz gs shape: {results['schwartz']['gs'].shape}, sample: {results['schwartz']['gs'][:3]}")
    print(f"pH shape: {results['pH'].shape}, sample: {results['pH'][:3]}")
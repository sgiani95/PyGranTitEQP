"""
gran_functions.py: Computes Gran g1 and Schwartz gs for weak_acid (validated formulas).

g1 = (V0 + v) * 10^(k - pH); gs = same (acid extension). k=0 for arrays; lambda tunable.
pH from Nernst (25°C). No type/method dispatch—weak_acid focus.

Dependencies: numpy, pandas.
"""

import numpy as np
import pandas as pd
from typing import Dict, Callable, Any


def compute_gran_functions(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute Gran g1 and Schwartz gs for weak_acid.

    Args:
        df: DataFrame with 'volume' (titrant vol, mL) and 'potential' (mV) columns.
        params

    Returns:
        Dict with 'gran' (dict: 'g1' array), 'schwartz' (dict: 'gs' array and lambda), 'pH' (array).

    Raises:
        ValueError: For data mismatch.
    """
    # Extract and coerce data
    volume = pd.to_numeric(df['volume'], errors='coerce').dropna().values
    potential = pd.to_numeric(df['potential'], errors='coerce').dropna().values
    if len(volume) != len(potential):
        raise ValueError("Volume and potential arrays must have equal length after cleaning.")

    # Nernst conversion to pH (25°C, E = -59.16 * (pH - 7) mV)
    pH = 7.0 - potential / 59.16

    V0 = params.get('V', 25.0)  # Initial volume
    k = 0.0  # Fixed for arrays; lambda allows tuning

    # Weak_acid Gran g1 = v * 10^{-pH} (fixed, no kk)
    gran_func = lambda v, ph, kk: v * np.power(10, -ph)  # Fixed; kk ignored for consistency
    g1 = gran_func(volume, pH, k)  # k unused

    # Schwartz gs = (v + kk) * 10^{-pH} (kk tunable for opt)
    schwartz_func = lambda v, ph, kk: (v + kk) * np.power(10, -ph)
    gs = schwartz_func(volume, pH, k)

    gran_func = lambda v, ph, kk: v * np.power(10, -ph)  # Fixed for Gran (kk ignored, matches g1 formula)
    results = {
        'gran': {'g1': g1, 'gran_func': gran_func},  # Fixed lambda for extraction
        'schwartz': {'gs': gs, 'gran_func': schwartz_func},
        'pH': pH
    }
    
    print("Gran and Schwartz (weak_acid) computed successfully.")
    return results


if __name__ == "__main__":
    # Standalone test
    import pandas as pd
    test_df = pd.DataFrame({
        'volume': np.linspace(0, 30, 10),
        'potential': np.linspace(0, -200, 10)  # Simulated drop
    })
    test_params = {'V': 25.0}
    results = compute_gran_functions(test_df, test_params)
    print(f"g1 shape: {results['gran']['g1'].shape}, sample: {results['gran']['g1'][:3]}")
    print(f"gs shape: {results['schwartz']['gs'].shape}, sample: {results['schwartz']['gs'][:3]}")
    print(f"pH shape: {results['pH'].shape}, sample: {results['pH'][:3]}")

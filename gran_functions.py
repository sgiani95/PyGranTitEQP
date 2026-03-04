"""
gran_functions.py: Computes Gran g1 and Schwartz gs functions for different titration types.
Currently implements acid_base (weak-acid version).
Other types (complexometric, precipitation, redox) raise NotImplementedError as placeholders.
Returns arrays and tunable lambda for analyzer/visualizer.
"""

import numpy as np
import pandas as pd
from typing import Dict, Callable, Any


def compute_gran_functions(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point: dispatches to the correct formula based on titration_type.
    Uses preprocessed volume and potential (flipped if base).
    """
    titration_type = params.get('titration_type', 'acid_base')

    # Extract preprocessed arrays
    volume = params['volume_array']
    potential = params['potential_array']  # Use preprocessed (flipped if base) array
    
    # Nernst pH conversion (25°C, 59.16 mV/pH)
    pH = 7.0 - potential / 59.16

    # Initial volume (used in some formulas)
    V0 = params.get('V', 25.0)

    match titration_type:
        case 'acid_base':
            # Weak-acid Gran/Schwartz (current implementation)
            k = 0.0  # Fixed for Gran

            # Gran: fixed g1 = v * 10^(-pH)
            gran_func = lambda v, ph, k: v * np.power(10, -ph)
            g1 = gran_func(volume, pH, k)

            # Schwartz: tunable gs = (v + k) * 10^(-pH)
            schwartz_func = lambda v, ph, k: (v + k) * np.power(10, -ph)
            gs = schwartz_func(volume, pH, k)  # computed with k=0

        case 'complexometric':
            raise NotImplementedError("Complexometric titration formulas not yet implemented")

        case 'precipitation':
            raise NotImplementedError("Precipitation titration formulas not yet implemented")

        case 'redox':
            raise NotImplementedError("Redox titration formulas not yet implemented")

        case _:
            raise ValueError(f"Unknown titration type: {titration_type}. Supported: acid_base, complexometric, precipitation, redox")

    results = {
        'gran': {
            'g1': g1,
            'gran_func': gran_func  # fixed lambda for Gran
        },
        'schwartz': {
            'gs': gs,
            'gran_func': schwartz_func  # tunable lambda for Schwartz
        },
        'pH': pH
    }
    
    return results


if __name__ == "__main__":
    # Standalone test (acid_base)
    import pandas as pd
    test_df = pd.DataFrame({
        'volume': np.linspace(0, 30, 10),
        'potential': np.linspace(0, -200, 10)  # Simulated acid drop
    })
    test_params = {
        'V': 25.0,
        'volume_array': test_df['volume'].values,
        'potential_array': test_df['potential'].values,
        'titration_type': 'acid_base'
    }
    results = compute_gran_functions(test_df, test_params)
    print(f"g1 shape: {results['gran']['g1'].shape}, sample: {results['gran']['g1'][:3]}")
    print(f"gs shape: {results['schwartz']['gs'].shape}, sample: {results['schwartz']['gs'][:3]}")
    print(f"pH shape: {results['pH'].shape}, sample: {results['pH'][:3]}")

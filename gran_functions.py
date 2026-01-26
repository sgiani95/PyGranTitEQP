# gran_functions.py: Module 3 for GranTED - Gran Function Computation

#######################
# Core Functionality: #
#######################
#
# Gran Computation: Calculates Gran functions for strong/weak acid/base titrations based on titration_type.
# Supports 4 cases: strong_acid_g1, weak_acid_g1, strong_base_g1, weak_base_g1, with single tunable k.
#
# pH Conversion: Converts 'potential' (mV) to pH = 7 - (potential / 59.16) for calculations.
#
# Output: Returns dict {'g1': array, 'gran_func': callable(v, ph, k)} for analyzer.py; screened dicts if k_range provided.
# Note: Default titration_type='weak_acid'; set via params (CLI/JSON/GUI).

import numpy as np
import pandas as pd

def compute_gran_functions(df, params, k_range=None):
    """
    Compute Gran function for the specified titration type (acid/base, strong/weak).
    Args:
        df (pd.DataFrame): Data with 'volume' and 'potential' columns.
        params (dict): From preprocess.py (e.g., {'V': 25.0, 'titration_type': 'weak_acid'}).
        k_range (list): Optional k values for screening (placeholder).
    Returns:
        dict: {'g1': array, 'gran_func': callable(v, ph, k)} for optimization; screened if k_range.
    """
    # Ensure numeric types
    volume = pd.to_numeric(df['volume'], errors='coerce').to_numpy()
    potential = pd.to_numeric(df['potential'], errors='coerce').to_numpy()
    pH = 7 - (potential / 59.16)  # Convert mV to pH

    V = float(params.get('V', 25.0))
    titration_type = params.get('titration_type', 'weak_acid')  # Default weak_acid
    k_default = float(params.get('k', 0.0))  # Default k for computation

    # Select Gran function based on titration_type
    if titration_type == 'strong_acid':
        g1 = (volume + V) * np.power(10, k_default - pH)
        gran_func = lambda v, ph, k: (v + V) * np.power(10, k - ph)
        print(f"Using strong_acid_g1 with V={V}, k={k_default}")

#########################################################################

    elif titration_type == 'weak_acid':
        g1 = (volume + k_default) * np.power(10, - pH)
        gran_func = lambda v, ph, k: (v+k) * np.power(10, - ph)
        
        print("Using Case 1 modified Gran function (moderately weak acid)")

#########################################################################

    elif titration_type == 'weak_acidd':
        g1 = volume * np.power(10, k_default - pH)
        gran_func = lambda v, ph, k: v * np.power(10, k - ph)
        print(f"Using weak_acid_g1 with k={k_default}")

    elif titration_type == 'strong_base':
        g1 = (volume + V) * np.power(10, k_default + pH)
        gran_func = lambda v, ph, k: (v + V) * np.power(10, k + ph)
        print(f"Using strong_base_g1 with V={V}, k={k_default}")
    
    elif titration_type == 'weak_base':
        g1 = volume * np.power(10, k_default + pH)
        gran_func = lambda v, ph, k: v * np.power(10, k + ph)
        print(f"Using weak_base_g1 with k={k_default}")
    else:
        raise ValueError(f"Unknown titration_type '{titration_type}'; use 'strong_acid', 'weak_acid', 'strong_base', or 'weak_base'.")

    results = {
        'g1': g1,  # Computed array with default k
        'gran_func': gran_func,  # Callable for analyzer optimization
    }

    # Placeholder for k-screening (TODO: Enable for multiple k trials)
    if k_range is not None:
        results['g1_screened'] = {}
        for k in k_range:
            results['g1_screened'][f'k={k}'] = gran_func(volume, pH, k)

    print(f"Computed Gran function for {titration_type} with default k={k_default}")
    return results
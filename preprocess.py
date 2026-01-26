# preprocess.py: Module 2 for GranTED - Data Preprocessing and Parameter Setup

#######################
# Core Functionality: #
#######################
#
# Parameter Configuration: Loads and validates user parameters (e.g., V=25 mL, C_B=0.1 M, titration_type='weak_acid')
# via hybrid input (CLI, JSON file, or interactive prompts), ensuring defaults for monoprotic acid-base titrations.
#
# Data Preparation: Converts raw DataFrame (from data_io.py) to NumPy arrays (volume, potential, pH via mV-to-pH: pH = 7 - (potential/59.16)),
# merging params for downstream use.
#
# Output: Returns the raw DataFrame and a params dict for gran_functions.py/analyzer.py; no transformation.

import numpy as np
import json
import pandas as pd

def get_config_from_cli_or_file_or_prompt(config_file=None, args=None):
    """
    Hybrid parameter loading: CLI (argparse), file (JSON), or interactive prompts.
    Args:
        config_file (str): Path to JSON config file (optional).
        args (dict): CLI args from argparse (optional).
    Returns:
        dict: Config with defaults (V=25, C_B=0.1, titration_type='weak_acid', etc.).
    """
    config = {
        'V': 25.0,  # Initial volume offset (mL)
        'C_B': 0.1,  # Titrant concentration (M)
        'r2_threshold': 0.95,  # For linearity checks
        'titration_type': 'weak_acid',  # 'strong_acid', 'weak_acid', 'strong_base', 'weak_base'
    }

    # Load from file if provided
    if config_file:
        with open(config_file, 'r') as f:
            file_config = json.load(f)
        config.update(file_config)
        print(f"Loaded config from {config_file}")

    # Override with CLI args if provided
    if args:
        config.update(vars(args))
        print("Applied CLI overrides")

    # Interactive prompts for missing keys
    for key in ['V', 'C_B', 'titration_type']:
        if key not in config or config[key] is None:
            default = config.get(key, 'default')
            value = input(f"Enter {key} (default {default}): ") or str(default)
            config[key] = value if key == 'titration_type' else float(value)

    # Validate titration params
    if config['titration_type'] not in ['strong_acid', 'weak_acid', 'strong_base', 'weak_base']:
        print("Warning: titration_type must be 'strong_acid', 'weak_acid', 'strong_base', or 'weak_base'.")
        config['titration_type'] = 'weak_acid'  # Fallback

    print("Final config:", config)
    return config

def preprocess_pipeline(df, config_overrides=None, config_file=None):
    """
    Main preprocessing routine: Prepare arrays, set params.
    Args:
        df (pd.DataFrame): Raw data with 'volume' and 'potential' columns.
        config_overrides (dict): CLI overrides (optional).
        config_file (str): Path to JSON config (optional).
    Returns:
        tuple: (df, params_dict).
    """
    config = get_config_from_cli_or_file_or_prompt(config_file, config_overrides)

    # Prepare arrays for analyzer
    params = {
        'volume': df['volume'].values,
        'potential': df['potential'].values,
    }
    params.update(config)  # Merge with user params

    print("Preprocessing complete. Ready for analysis.")
    return df, params

# Example usage (for testing)
if __name__ == "__main__":
    df = pd.read_csv('data.dat', sep='\s+', names=['volume', 'potential'])
    df_processed, params = preprocess_pipeline(df, config_file='config.json')
    print("Processed params:", params)
"""
preprocess.py: Module for parameter configuration and data preparation for titration analysis.

Handles hybrid input (CLI args, JSON config, prompts) with fallbacks to defaults.
Auto-detects acid/base via linear slope for acid_base type; flips potential for bases.
Focus: Acid-base only at the moment; placeholders for complexometric, precipitation, redox.
"""

import json
import pandas as pd
import numpy as np
from scipy.stats import linregress
from typing import Dict, Any, Tuple, Optional


def get_config_from_cli_or_file_or_prompt(
    config_file: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    interactive: bool = True
) -> Dict[str, Any]:
    """
    Load and validate configuration parameters with fallback chain:
    JSON file -> CLI args -> interactive prompts -> defaults.

    Updated valid types: acid_base, complexometric, precipitation, redox.
    Placeholder fallback to acid_base.
    """
    config = {
        'V': 50.0,  # Initial volume (mL)
        'C_B': 0.1,  # Titrant concentration (M)
        'titration_type': 'acid_base',  # Default
        'r2_threshold': 0.95
    }
    valid_types = ['acid_base', 'complexometric', 'precipitation', 'redox']

    # Load from JSON if provided
    if config_file:
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            config.update(file_config)
            print(f"Loaded config from '{config_file}'.")
        except FileNotFoundError:
            print(f"Warning: Config file '{config_file}' not found. Using defaults.")
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid config file '{config_file}': {e}. Check JSON format and keys.")

    # Override from CLI args if provided
    if args:
        for key, value in args.items():
            if key in config:
                try:
                    config[key] = float(value) if key in ['V', 'C_B', 'r2_threshold'] else str(value)
                except ValueError:
                    raise ValueError(f"Invalid value '{value}' for '{key}': Must be numeric for V/C_B/r2_threshold.")

    # Interactive prompts for missing/override
    required_keys = ['V', 'C_B', 'titration_type']
    for key in required_keys:
        if key not in config or config[key] is None:
            if interactive:
                prompt = {
                    'V': "Enter initial volume V (mL, default 25): ",
                    'C_B': "Enter titrant concentration C_B (M, default 0.1): ",
                    'titration_type': "Enter titration type (acid_base/complexometric/precipitation/redox, default acid_base): "
                }
                user_input = input(prompt.get(key, f"Enter {key} (default {config.get(key, 'N/A')}): "))
                if user_input.strip():
                    try:
                        config[key] = float(user_input) if key in ['V', 'C_B'] else user_input.strip()
                    except ValueError:
                        print(f"Warning: Invalid input '{user_input}' for {key}. Using default.")
            else:
                if key == 'titration_type':
                    raise ValueError("titration_type required but not provided in non-interactive mode.")
                print(f"Warning: {key} required but missing in non-interactive mode. Using default {config[key]}.")

    # Validate titration_type (placeholder for future types)
    if config['titration_type'] not in valid_types:
        print(
            f"Warning: Invalid titration_type '{config['titration_type']}': Must be one of {valid_types}. "
            f"Using fallback 'acid_base' (other types are placeholders)."
        )
        config['titration_type'] = 'acid_base'

    print(f"Final config: {config}")
    return config


def preprocess_pipeline(
    df: pd.DataFrame,
    config_overrides: Optional[Dict[str, Any]] = None,
    config_file: Optional[str] = None,
    interactive: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Orchestrate preprocessing: Load config, extract arrays, auto-detect acid/base for acid_base type.
    For acid_base: linear slope check; flip potential if base (slope >= 0).
    Returns (df, params) — df potential possibly flipped, params includes arrays and config.
    """
    # Load and validate config
    config = get_config_from_cli_or_file_or_prompt(config_file, config_overrides, interactive)

    # Extract arrays
    params = {
        'volume_array': df['volume'].values,
        'potential_array': df['potential'].values
    }
    params.update(config)

    # Auto-detect for acid_base only
    if params['titration_type'] == 'acid_base':
        volume = params['volume_array']
        potential = df['potential'].values  # Modify df in-place

        # Linear interpolation: slope from linregress
        slope, intercept, r_value, _, _ = linregress(volume, potential)
        print(f"Detected slope = {slope:.3f} (R = {r_value:.3f})")

        if slope >= 0:  # Increasing potential → base titration
            print("Detected base titration (positive slope). Flipping sign and setting type.")
            df['potential'] *= -1
            params['potential_array'] *= -1
            params['is_base'] = True
        else:  # Decreasing potential → acid titration
            print("Detected acid titration (negative slope). No flip.")
            params['is_base'] = False

    else:
        # Placeholder for other types (no detection/flip)
        print(f"Titration type '{params['titration_type']}' — no auto-detection/flip (placeholder).")
        params['is_base'] = False  # Default

    print("Preprocessing complete: Arrays extracted, params merged, type auto-detected (if acid_base).")
    print(df)
    return df, params


if __name__ == "__main__":
    # Standalone test stub
    try:
        df = pd.read_csv('data.dat', sep=r'\s+', header=None, names=['volume', 'potential'])
        result_df, result_params = preprocess_pipeline(df, interactive=True)
        print("Test successful!")
        print(f"Output params keys: {list(result_params.keys())}")
        print(f"Detected type: {result_params['titration_type']}, is_base: {result_params.get('is_base', False)}")
    except Exception as e:
        print(f"Test failed: {e}")
"""
preprocess.py: Module for parameter configuration and data preparation for titration analysis.

Handles hybrid input (CLI args, JSON config, prompts) with fallbacks to defaults for acid-base titrations.
Extracts volume and potential arrays from DataFrame; merges into params dict for downstream use.
Focus: Acid-base only; extensible to precipitation/complex/redox in future.

Dependencies: numpy, json, pandas.
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional


def get_config_from_cli_or_file_or_prompt(
    config_file: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    interactive: bool = True
) -> Dict[str, Any]:
    """
    Load and validate configuration parameters with fallback chain:
    JSON file -> CLI args -> interactive prompts -> defaults.

    Args:
        config_file: Path to JSON config file (optional).
        args: Dict of CLI arguments (optional).
        interactive: If False, skip prompts and use defaults for missing keys.

    Returns:
        Dict of validated params.

    Raises:
        ValueError: For invalid titration_type or missing required keys in non-interactive mode.
    """
    # Defaults for acid-base titrations
    config = {
        'V': 25.0,  # Initial volume (mL)
        'C_B': 0.1,  # Titrant concentration (M)
        'titration_type': 'weak_acid',
        'r2_threshold': 0.95
    }
    valid_types = ['weak_acid', 'strong_acid', 'weak_base', 'strong_base']

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
                    'titration_type': "Enter titration type (weak_acid/strong_acid/weak_base/strong_base, default weak_acid): "
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

    # Validate titration_type (soft fallback)
    if config['titration_type'] not in valid_types:
        print(
            f"Warning: Invalid titration_type '{config['titration_type']}': Must be one of {valid_types}. "
            f"Using fallback 'weak_acid'."
        )
        config['titration_type'] = 'weak_acid'

    print(f"Final config: {config}")
    return config


def preprocess_pipeline(
    df: pd.DataFrame,
    config_overrides: Optional[Dict[str, Any]] = None,
    config_file: Optional[str] = None,
    interactive: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Orchestrate preprocessing: Load config, extract arrays, merge params.

    Args:
        df: Input DataFrame with 'volume' and 'potential' columns.
        config_overrides: Dict of CLI args for config.
        config_file: Path to JSON config.
        interactive: Enable interactive prompts.

    Returns:
        Tuple (df, params) where params includes arrays and config.

    Raises:
        ValueError: For invalid config.
    """
    # Load and validate config
    config = get_config_from_cli_or_file_or_prompt(config_file, config_overrides, interactive)

    # Extract arrays (assumes columns from data_io.py)
    params = {
        'volume_array': df['volume'].values,
        'potential_array': df['potential'].values
    }
    params.update(config)

    print("Preprocessing complete: Arrays extracted and params merged.")
    return df, params


if __name__ == "__main__":
    # Standalone test: Load sample data directly
    try:
        df = pd.read_csv('data.dat', sep=r'\s+', header=None, names=['volume', 'potential'])
        result_df, result_params = preprocess_pipeline(df, interactive=True)
        print("Test successful!")
        print(f"Output params keys: {list(result_params.keys())}")
    except Exception as e:
        print(f"Test failed: {e}")

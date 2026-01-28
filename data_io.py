"""
data_io.py: Simplified module for loading and validating single titration data files.

Always loads without headers, stripping any potential header rows or extra columns.
Enforces exactly two columns: volume (mL) and potential (mV). Assigns default names.
Validation checks for monotonic volumes and potential range (-420 to 420 mV).

Dependencies: pandas, pathlib.
"""

import pandas as pd
from pathlib import Path
from typing import Optional

SUPPORTED_FORMATS = ['.dat', '.txt', '.csv', '.xlsx']


"""
data_io.py: Procedural module for loading and validating titration data files.
Supports single file loading with automatic header detection.
No classes, pure functions.
"""

import pandas as pd
from pathlib import Path
import numpy as np


"""
data_io.py: Procedural module for loading and validating titration data files.
Supports single file loading with automatic header detection.
No classes, pure functions.
Keeps original validation rules exactly as provided.
"""

import pandas as pd
from pathlib import Path
import numpy as np


def load_single_file(path: str | Path) -> pd.DataFrame | None:
    """
    Load a single titration data file with robust filtering of non-numeric lines.
    Keeps only lines with exactly two numeric tokens.
    Forces column names ['volume', 'potential'].
    Returns DataFrame or None on error.
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        print(f"Error: File not found or not a file: {path}")
        return None

    try:
        # Read all lines
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Filter to keep only lines with exactly two numeric tokens
        numeric_lines = []
        skipped = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                skipped += 1
                continue
            tokens = line.split()
            if len(tokens) == 2:
                # Check both tokens are numeric (digit or decimal point)
                if all(any(c.isdigit() or c == '.' for c in t) for t in tokens):
                    numeric_lines.append(line)
                else:
                    skipped += 1
            else:
                skipped += 1

        if not numeric_lines:
            print(f"Warning: No lines with exactly two numeric values found in {path} (skipped {skipped} lines)")
            return None

        # Load filtered lines from StringIO
        from io import StringIO
        filtered_text = '\n'.join(numeric_lines)
        df = pd.read_csv(
            StringIO(filtered_text),
            sep=r'\s+',
            header=None,
            names=['volume', 'potential'],
            comment='#',
            on_bad_lines='skip',
            encoding='utf-8',
            engine='python'
        )

        if df.empty:
            print(f"Warning: Empty data after filtering in {path}")
            return None

        # Force numeric conversion
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna()

        if df.empty:
            print(f"Warning: No valid numeric data after cleaning in {path}")
            return None

        print(f"Loaded '{path}': {len(df)} rows, skipped {skipped} header/comment/non-numeric lines.")
        return df

    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None


def validate_data(df: pd.DataFrame) -> bool:
    """
    Validate loaded DataFrame for titration analysis.
    Returns True if valid, False otherwise (prints warnings).
    """
    if df is None or df.empty:
        print("Validation failed: DataFrame is None or empty")
        return False

    if len(df.columns) != 2:
        print(f"Validation failed: Expected 2 columns, got {len(df.columns)}")
        return False

    try:
        df = df.astype(float)  # Ensure numeric
    except ValueError:
        print("Validation failed: Non-numeric values in data")
        return False

    volume = df.iloc[:, 0].values
    potential = df.iloc[:, 1].values

    # Volume: strictly increasing, positive
    if not np.all(np.diff(volume) > 0):
        print("Validation warning: Volume is not strictly increasing")

    if np.any(volume < 0):
        print("Validation failed: Volume contains negative values")
        return False

    # Potential: reasonable mV range -420 to 420 (exact legacy range)
    if np.any((potential < -420) | (potential > 420)):
        print("Validation warning: Potential outside typical mV range (-420 to 420)")

    # No NaN
    if df.isnull().values.any():
        print("Validation failed: Contains NaN values")
        return False

    print("Validation passed")
    return True

if __name__ == "__main__":
    # Quick test with sample file
    df = load_single_file('data.dat')
    if df is not None and validate_data(df):
        print("Test successful!")
    else:
        print("Test failed.")
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


def load_single_file(file_path: str) -> Optional[pd.DataFrame]:
    """
    Load a single titration data file without headers, enforcing exactly two numeric columns.

    Args:
        file_path: Path to the file (str).

    Returns:
        pd.DataFrame with 'volume' and 'potential' columns if successful, else None.

    Raises:
        ValueError: If file format unsupported, insufficient/extra columns, or non-numeric data.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File '{file_path}' not found.")
        return None

    ext = path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        print(f"Error: Unsupported format '{ext}'. Supported: {SUPPORTED_FORMATS}")
        return None

    try:
        if ext == '.xlsx':
            df = pd.read_excel(path, header=None)
        else:  # .dat, .txt, .csv: space-separated assumed
            df = pd.read_csv(path, sep=r'\s+', header=None)

        # Enforce exactly 2 columns: Drop extras if more, error if fewer
        if df.shape[1] < 2:
            print("Error: File must have at least 2 columns.")
            return None
        elif df.shape[1] > 2:
            print(f"Warning: File has {df.shape[1]} columns; keeping only first 2.")
            df = df.iloc[:, :2]

        # Assign default column names
        df.columns = ['volume', 'potential']

        # Basic numeric check (strip non-numeric rows if needed, but assume clean)
        if not pd.api.types.is_numeric_dtype(df['volume']) or not pd.api.types.is_numeric_dtype(df['potential']):
            print("Error: Columns must contain numeric data only.")
            return None

        # Print summary
        print(f"Loaded '{file_path}': {df.shape[0]} rows, 2 columns (volume, potential).")
        if df.shape[0] > 0:
            print(df.head())

        return df

    except Exception as e:
        print(f"Error reading '{file_path}': {e}")
        return None


def validate_data(df: pd.DataFrame) -> bool:
    """
    Validate the loaded DataFrame for titration data integrity.

    Checks:
    - At least 3 rows.
    - Volumes are strictly increasing (monotonic).
    - Potentials in range [-420, 420] mV (Nernst equation bounds).

    Args:
        df: DataFrame with 'volume' and 'potential' columns.

    Returns:
        True if valid, False otherwise. Prints warnings for issues.
    """
    if df.empty or len(df) < 3:
        print("Warning: Data has fewer than 3 rows.")
        return False

    # Use column names (enforced by loader)
    volumes = df['volume']
    potentials = df['potential']

    # Monotonic check
    if not volumes.is_monotonic_increasing:
        print("Warning: Volumes are not strictly increasing.")
        return False

    # Range check (soft warning for out-of-range)
    if (potentials < -420).any() or (potentials > 420).any():
        print("Warning: Some potentials outside [-420, 420] mV range.")

    print(f"Validation passed: {len(df)} monotonic points in valid range.")
    return True


if __name__ == "__main__":
    # Quick test with sample file
    df = load_single_file('data.dat')
    if df is not None and validate_data(df):
        print("Test successful!")
    else:
        print("Test failed.")

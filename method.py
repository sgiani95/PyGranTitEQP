# method.py
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

from data_io import load_data
from preprocess import preprocess
from analyzer import analyze_gran
from visualizer import (
    plot_gran_schwartz,
    plot_all_combined,
    plot_titration_curve,
)
from reporter import generate_csv_report


def trim_data(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    Return trimmed or full data depending on mode.
    Currently placeholder logic — customize per mode later.
    """
    if mode == "debug":
        return df.head(20)  # small slice for quick testing
    if mode == "method validation":
        return df.iloc[5:30]  # example subset
    if mode == "method application":
        return df.iloc[10:]   # example
    return df  # default: full data for development


def get_plots_for_mode(mode: str) -> List:
    """
    Return list of plot functions to call for this mode.
    Only using existing plot functions from visualizer.py.
    """
    if mode == "method development":
        return [plot_gran_schwartz]
    elif mode == "method validation":
        return [plot_all_combined]
    elif mode == "method application":
        return [plot_titration_curve]
    elif mode == "debug":
        return [plot_titration_curve]  # placeholder — change later
    return [plot_titration_curve]  # fallback


def run_method(
    mode: str,
    input_path: str | Path,
    output_dir: Path,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Orchestrates the workflow for the chosen mode.
    Uses only real functions from your repo.
    """
    print(f"Starting workflow in mode: {mode}")

    # 1. Load & trim
    df_raw = load_data(input_path)
    df = trim_data(df_raw, mode)

    # 2. Preprocess & analyze (common to all modes)
    df_pre = preprocess(df)
    params = {}  # extend later if needed (e.g. from args or config)
    results = analyze_gran(df_pre, params, verbose=verbose)

    # 3. Generate selected plots
    for plot_func in get_plots_for_mode(mode):
        plot_func(results, params, output_dir=output_dir)

    # 4. Report (current CSV for development, placeholder message for others)
    if mode == "method development":
        generate_csv_report(results, output_dir / "report.csv")
    else:
        print(f"[Placeholder] No report yet for mode '{mode}'")

    print(f"Workflow '{mode}' completed.")
    return {"results": results, "mode": mode}

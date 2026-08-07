"""
End-to-end test for method_development report.csv
"""

import pytest
from pathlib import Path
import sys

# Make sure the package is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from granted.main import main  # or the function you normally call
# Alternative if you prefer calling the pipeline more directly:
# from granted.modes import run_mode
# from granted import data_io, preprocess, ...

from .conftest import read_report_csv


def test_method_development_report(data_development, tmp_output_dir, monkeypatch):
    """
    Run method_development on the dedicated sample and check key report values.
    """
    # --- Arrange ---
    # We simulate the CLI arguments
    args = [
        "granted",
        "--data_file", str(data_development),
        "--mode", "method_development",
        "--output_dir", str(tmp_output_dir),
    ]

    # --- Act ---
    # Patch sys.argv and call main()
    monkeypatch.setattr(sys, "argv", args)
    main()

    # --- Assert ---
    report_path = tmp_output_dir / "report.csv"
    df = read_report_csv(report_path)

    # Helper to get a row by Method name
    def get_row(method_name: str):
        row = df[df["Method"] == method_name]
        assert not row.empty, f"Row '{method_name}' not found in report"
        return row.iloc[0]

    # 1. Gran Raw (full data)
    gran_raw = get_row("Gran Raw (full data)")
    assert abs(float(gran_raw["V_eq [mL]"]) - 5.017) < 0.01

    # 2. Schwartz Optimized (full data)
    sch_opt = get_row("Schwartz Optimized (full data)")
    assert abs(float(sch_opt["V_eq [mL]"]) - 5.005) < 0.01

    # 3. Vopt Result
    vopt = get_row("Vopt Result")
    assert abs(float(vopt["V_eq [mL]"]) - 5.002) < 0.01
    assert abs(float(vopt["R²"]) - 0.9997) < 0.001
    assert abs(float(vopt["Max Volume Used [mL]"]) - 4.400) < 0.05

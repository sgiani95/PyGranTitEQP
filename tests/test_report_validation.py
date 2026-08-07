"""
End-to-end test for method_validation report.
"""

import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from granted.main import main
from .conftest import read_report_csv


def test_method_validation_report(data_validation, tmp_output_dir, monkeypatch):
    """
    Run method_validation on the dedicated sample and check key report values.
    """
    # --- Arrange ---
    args = [
        "granted",
        "--data_file", str(data_validation),
        "--mode", "method_validation",
        "--vopt", "4.400",
        "--output_dir", str(tmp_output_dir),
        "--verbose",
    ]

    # --- Act ---
    monkeypatch.setattr(sys, "argv", args)
    main()

    # --- Assert ---
    report_path = tmp_output_dir / "validation_report.csv"
    df = read_report_csv(report_path)

    def get_row(method_name: str):
        row = df[df["Method"] == method_name]
        assert not row.empty, f"Row '{method_name}' not found in report"
        return row.iloc[0]

    # 1. Gran Raw (full validation)
    gran_raw = get_row("Gran Raw (full validation)")
    assert abs(float(gran_raw["V_eq [mL]"]) - 5.017) < 0.01

    # 2. Schwartz Optimized (full validation)
    sch_opt = get_row("Schwartz Optimized (full validation)")
    assert abs(float(sch_opt["V_eq [mL]"]) - 5.005) < 0.01

    # 3. Vopt Result (validation)
    vopt = get_row("Vopt Result (validation)")
    assert abs(float(vopt["V_eq [mL]"]) - 5.002) < 0.01
    assert abs(float(vopt["R²"]) - 0.9997) < 0.001
    assert "4.400" in str(vopt["Notes"])

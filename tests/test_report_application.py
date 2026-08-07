"""
End-to-end test for method_application report.
"""

import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from granted.main import main
from .conftest import read_report_csv


def test_method_application_report(data_application, tmp_output_dir, monkeypatch):
    """
    Run method_application on the dedicated sample and check key report values.
    """
    # --- Arrange ---
    args = [
        "granted",
        "--data_file", str(data_application),
        "--mode", "method_application",
        "--output_dir", str(tmp_output_dir),
        "--verbose",
    ]

    # --- Act ---
    monkeypatch.setattr(sys, "argv", args)
    main()

    # --- Assert ---
    report_path = tmp_output_dir / "application_report.csv"
    df = read_report_csv(report_path)

    def get_row(method_name: str):
        row = df[df["Method"] == method_name]
        assert not row.empty, f"Row '{method_name}' not found in report"
        return row.iloc[0]

    # 1. Gran Raw
    gran_raw = get_row("Gran Raw")
    assert abs(float(gran_raw["V_eq [mL]"]) - 5.031) < 0.01

    # 2. Schwartz Optimized
    sch_opt = get_row("Schwartz Optimized")
    assert abs(float(sch_opt["V_eq [mL]"]) - 5.002) < 0.01

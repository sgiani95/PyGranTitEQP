"""
Shared fixtures for GranTED tests.
"""

import pytest
from pathlib import Path
import pandas as pd
import tempfile
import shutil

# Project root (tests/ is one level below root)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


@pytest.fixture
def data_development():
    """Path to the dedicated development sample file."""
    path = DATA_DIR / "data_development.dat"
    assert path.exists(), f"Missing test data: {path}"
    return path


@pytest.fixture
def data_validation():
    """Path to the dedicated validation sample file."""
    path = DATA_DIR / "data_validation.dat"
    assert path.exists(), f"Missing test data: {path}"
    return path


@pytest.fixture
def data_application():
    """Path to the dedicated application sample file."""
    path = DATA_DIR / "data_application.dat"
    assert path.exists(), f"Missing test data: {path}"
    return path


@pytest.fixture
def tmp_output_dir():
    """Temporary output directory that is cleaned up after the test."""
    tmp = Path(tempfile.mkdtemp(prefix="granted_test_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def read_report_csv(report_path: Path) -> pd.DataFrame:
    """Helper to read a GranTED report.csv into a DataFrame."""
    assert report_path.exists(), f"Report not found: {report_path}"
    return pd.read_csv(report_path)

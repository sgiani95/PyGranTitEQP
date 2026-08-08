"""
GranTED — Gran/Schwartz Titration Analysis Tool
An open-source package for automated potentiometric titration analysis.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("granted")
except PackageNotFoundError:
    # Fallback when the package is not installed (e.g. running sources directly)
    __version__ = "0.3.14"

__author__ = "sgiani95"
__license__ = "Apache-2.0"
__description__ = (
    "Automated Gran and Schwartz titration equivalence point determination "
    "with uncertainty and diagnostics."
)

# Public API
from .main import main
from .analyzer import analyze_gran
from .visualizer import (
    plot_titration_curve,
    plot_gran_schwartz,
    plot_development_summary,
)
from .reporter import (
    generate_csv_report_development,
    generate_csv_report_validation,
    generate_csv_report_application,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "__description__",
    "main",
    "analyze_gran",
    "plot_titration_curve",
    "plot_gran_schwartz",
    "plot_development_summary",
    "generate_csv_report_development",
    "generate_csv_report_validation",
    "generate_csv_report_application",
]

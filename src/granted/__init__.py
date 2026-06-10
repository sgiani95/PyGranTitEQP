"""
GranTED — Gran/Schwartz Titration Analysis Tool
An open-source package for automated potentiometric titration analysis.
"""

__version__ = "2.0.22"
__author__ = "Samuele Giani"
__license__ = "Apache-2.0"
__description__ = "Automated Gran and Schwartz titration equivalence point determination with uncertainty and diagnostics."

# Expose the most useful functions for users (clean API)
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
    "main",
    "analyze_gran",
    "plot_titration_curve",
    "plot_gran_schwartz",
    "plot_development_summary",
    "generate_csv_report_development",
    "generate_csv_report_validation",
    "generate_csv_report_application",
]

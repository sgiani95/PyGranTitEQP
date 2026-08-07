#!/usr/bin/env python3
"""
Launcher to run GranTED report tests in a fixed order:
1. method_development
2. method_validation
3. method_application
"""

import sys
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).parent
    tests_dir = root / "tests"

    # Explicit order
    test_files = [
        tests_dir / "test_report_development.py",
        tests_dir / "test_report_validation.py",
        tests_dir / "test_report_application.py",
    ]

    # Check that all files exist
    missing = [f for f in test_files if not f.exists()]
    if missing:
        print("Missing test files:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "pytest",
        *[str(f) for f in test_files],
        "-v"
    ]

    print("Running GranTED report tests (development → validation → application)...\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

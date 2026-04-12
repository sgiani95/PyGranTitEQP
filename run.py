#!/usr/bin/env python3
"""
Simple launcher for GranTED.
Usage: python run.py [arguments]
"""

import sys
from pathlib import Path

# Ensure the package can be found
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    from granted.main import main
    main()

#!/usr/bin/env python3
"""
Simple launcher for GranTED.
Usage: ./run.py [arguments]
"""

import sys
from pathlib import Path

# Ensure the package can be found when running from root
root = Path(__file__).parent
sys.path.insert(0, str(root / "src"))

if __name__ == "__main__":
    from granted.main import main
    main()

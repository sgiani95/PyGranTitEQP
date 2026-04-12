#!/usr/bin/env python3
"""
Simple launcher for GranTED.
Run with: python3 run.py [arguments]
"""

import sys
from pathlib import Path

# Add src to path so we can run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from granted.main import main

if __name__ == "__main__":
    main()

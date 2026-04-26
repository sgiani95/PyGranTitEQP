"""
main.py: CLI orchestrator for GranTED pipeline.
Supports --verbose for tracing; merges CLI > JSON > defaults for config.
Optional --skip-analysis (uses raw gran_results for visuals/report).
Defaults to 'data.dat' if no --data_file; graceful exit if missing.
"""

__version__ = "0.9.2"
#
# Pride versioning 🌈
#
# Given a version number PROUD.DEFAULT.SHAME, increment the:
# PROUD version when you make changes you are really proud of
# DEFAULT version when you make a release that's okay
# SHAME version when you are fixing things that are too embarrassing to admit


import argparse
import sys
import json
from pathlib import Path
import numpy as np

# Core imports
from granted import data_io
from granted import preprocess
from granted.gran_functions import compute_gran_functions
from granted import analyzer
from granted import visualizer
from granted import reporter
from granted.modes import run_mode


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='GranTED: Gran-Schwartz Titration Analysis')
    
    parser.add_argument('--data_file', default='data.dat', help='Path to titration data file (default: data.dat)')
    parser.add_argument('--V_0', type=float, default=25.0, help='Initial volume (mL)')
    parser.add_argument('--C', type=float, default=0.1, help='Titrant concentration (M)')
    parser.add_argument('--output_dir', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--config_file', help='Optional JSON config file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose tracing')
    parser.add_argument('--skip-analysis', action='store_true', help='Skip analyzer; use raw gran_results for visuals/report')
    parser.add_argument('--profile', action='store_true', help='Generate callgraph.svg')

    # Mode selection
    parser.add_argument(
        '--mode',
        type = str,
        choices = ['method_development', 'method_validation', 'method_application', 'method_debug'],
        default = 'method_development',
        help = 'Operation mode: method_development, method_validation, method_application, method_debug (default: method_development)' 
    )

    # Thresholds for earliest optimized volume detection
    parser.add_argument('--r2-min', type=float, default=0.99,
                        help='Minimum R² for acceptable fit (default: 0.99)')
    parser.add_argument('--unc-max', type=float, default=0.100,
                        help='Maximum allowed uncertainty on EQP (mL) (default: 0.100)')
    parser.add_argument('--veq-tolerance', type=float, default=0.010,
                        help='Maximum allowed deviation from final EQP (mL) (default: 0.010)')
    parser.add_argument('--stability-window', type=int, default=3,
                        help='Number of consecutive points that must satisfy criteria (default: 3)')
    parser.add_argument('--trim-forward', action='store_true',
                        help='Use forward trimming instead of backward (default is backward)')

    args = parser.parse_args()

    # Merge CLI > JSON > defaults
    if args.config_file:
        try:
            with open(args.config_file, 'r') as f:
                config = json.load(f)
            for key, value in config.items():
                if hasattr(args, key) and getattr(args, key) is not None:
                    continue
                if key in ['V_0', 'C'] and isinstance(value, (int, float)):
                    setattr(args, key, value)
            if args.verbose:
                print(f"Merged config from {args.config_file}")
        except Exception as e:
            print(f"Warning: Failed to load config {args.config_file}: {e}")

    return args


def main():
    """Orchestrate pipeline."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    if args.verbose:
        print("Starting GranTED pipeline...")

    df = None
    params = None
    analysis_results = None

    # Step 1: Load data
    try:
        if args.verbose:
            print("Loading data...")
        if not Path(args.data_file).exists():
            print(f"No {args.data_file} found—run with --data_file your_file.dat.")
            sys.exit(0)
        df = data_io.load_single_file(args.data_file)
        if df is None:
            raise ValueError(f"Failed to load {args.data_file}")
        if not data_io.validate_data(df):
            raise ValueError("Data validation failed")
        if args.verbose:
            print(f"Loaded {len(df)} points.")
    except Exception as e:
        print(f"Load error: {e}")
        sys.exit(1)

    # Step 2: Preprocess
    try:
        if args.verbose:
            print("Preprocessing...")
        _, params = preprocess.preprocess_pipeline(df, config_overrides=vars(args), interactive=False)
        if args.verbose:
            print(f"Params: V_0 = {params.get('V_0')}, C = {params.get('C')}, type={params.get('titration_type')}")
    except Exception as e:
        print(f"Preprocess error: {e}")
        sys.exit(1)

    # Step 3: Compute Gran-Schwartz
    try:
        if args.verbose:
            print("Computing functions...")
        gran_results = compute_gran_functions(df, params)
        if args.verbose:
            print("Gran-Schwartz computed.")
    except Exception as e:
        print(f"Compute error: {e}")
        sys.exit(1)

    # Step 4: Analyze
    try:
        if not args.skip_analysis:
            if args.verbose:
                print("Analyzing...")
            analysis_results = analyzer.analyze_gran(gran_results, params)
        else:
            if args.verbose:
                print("Skipping analysis (raw mode).")
            analysis_results = gran_results
        if args.verbose:
            print("Analysis complete.")
    except Exception as e:
        print(f"Analyze error: {e} (falling back to raw)")
        analysis_results = gran_results

    # Step 5: Mode orchestration

    mode_results = run_mode(
        mode=args.mode,
        df=df,
        params=params,
        output_dir=output_dir,
        verbose=args.verbose,
        r2_min=args.r2_min,
        unc_max=args.unc_max,
        veq_tolerance=args.veq_tolerance,
        stability_window=args.stability_window,
        trim_forward=args.trim_forward
    )

    if args.verbose:
        print(f"Mode '{args.mode}' complete.")


if __name__ == "__main__":
    from pycallgraph2 import PyCallGraph, Config
    from pycallgraph2.output import GraphvizOutput
    args = parse_args()
    if args.profile:
        output = GraphvizOutput(output_file = str(Path(args.output_dir) / 'callgraph.svg'))
        with PyCallGraph(output=output):
            main()
    else:
        main()

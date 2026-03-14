"""
main.py: CLI orchestrator for GranTED pipeline.
Supports --verbose for tracing; merges CLI > JSON > defaults for config.
Optional --skip-analysis (uses raw gran_results for visuals/report).
Defaults to 'data.dat' if no --data_file; graceful exit if missing.
Weak_acid focus—no type/method args (auto-detected in preprocess).
Full flow: load → preprocess → gran_functions → [analyzer] → visualizer → reporter.
Profiling via PyCallGraph if --profile.
Dependencies: argparse, sys, json, pathlib + core modules.
"""
__version__ = "0.9.2" # change manually on each significant update
# pride versioning: X.Y.Z
# X = proud_version(bump when you are proud of the release)
# Y = default_version(just normal/okay releases)
# Z = shame_version(bump when fixing things too embarrassing to admit)

import argparse
import sys
import json
from pathlib import Path

# Core imports
import data_io
import preprocess
from gran_functions import compute_gran_functions
import analyzer # Optional
import visualizer
import reporter

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='GranTED: Gran/Schwartz Titration Analysis')
    parser.add_argument('--data_file', default='data.dat', help='Path to titration data file (default: data.dat)')
    parser.add_argument('--V', type=float, default=25.0, help='Initial volume (mL)')
    parser.add_argument('--C_B', type=float, default=0.1, help='Titrant concentration (M)')
    parser.add_argument('--output_dir', default='./output', help='Output directory')
    parser.add_argument('--config_file', help='Optional JSON config file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose tracing')
    parser.add_argument('--skip-analysis', action='store_true', help='Skip analyzer; use raw gran_results for visuals/report')
    parser.add_argument('--profile', action='store_true', help='Generate callgraph.svg')

    # NEW: mode selection
    parser.add_argument(
        '--mode',
        type=str,
        choices=['method_development', 'method_validation', 'method_application', 'method_debug'],
        default='method_development',
        help='Operation mode: method_development | method_validation | method_application | method_debug'
    )

    args = parser.parse_args()

    # Structural: Merge CLI > JSON > defaults (if config_file)
    if args.config_file:
        try:
            with open(args.config_file, 'r') as f:
                config = json.load(f)
            # Override args with JSON (CLI takes precedence)
            for key, value in config.items():
                if hasattr(args, key) and getattr(args, key) is not None:
                    continue # CLI wins
                if key in ['V', 'C_B'] and isinstance(value, (int, float)):
                    setattr(args, key, value)
            if args.verbose:
                print(f"Merged config from {args.config_file}")
        except Exception as e:
            print(f"Warning: Failed to load config {args.config_file}: {e}")

    return args

def main():
    """Orchestrate pipeline with error chaining (Quick Win)."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    if args.verbose:
        print("Starting GranTED pipeline...")

    df = None
    params = None
    gran_results = None
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

    # Step 2: Preprocess (auto-detects weak_acid/weak_base)
    try:
        if args.verbose:
            print("Preprocessing...")
        _, params = preprocess.preprocess_pipeline(df, config_overrides=vars(args), interactive=False)
        if args.verbose:
            print(f"Params: V={params['V']}, C_B={params['C_B']}, type={params['titration_type']}")
    except Exception as e:
        print(f"Preprocess error: {e}")
        sys.exit(1)

    # Step 3: Compute Gran/Schwartz (weak_acid focus)
    try:
        if args.verbose:
            print("Computing functions...")
        gran_results = compute_gran_functions(df, params)
        if args.verbose:
            print("Gran/Schwartz computed.")
    except Exception as e:
        print(f"Compute error: {e}")
        sys.exit(1)

    # Step 4: Analyze (optional, with fallback)
    try:
        if not args.skip_analysis:
            if args.verbose:
                print("Analyzing...")
            analysis_results = analyzer.analyze_gran(gran_results, params) # Will raise if not implemented
        else:
            if args.verbose:
                print("Skipping analysis (raw mode).")
            analysis_results = gran_results # Direct pass; downstream fallbacks handle raw
        if args.verbose:
            print("Analysis complete.")
    except Exception as e:
        print(f"Analyze error: {e} (falling back to raw)")
        analysis_results = gran_results # Graceful raw fallback

    # Step 5: Orchestrator - mode-dependent visualization
    mode = args.mode
    print(f"Generating plots for mode: {mode}")

    if mode == 'method_development':
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        visualizer.plot_gran_schwartz(analysis_results, params, output_dir=output_dir)

    elif mode == 'method_validation':
        visualizer.plot_all_combined(df, params, analysis_results, output_dir=output_dir)

    elif mode == 'method_application':
        visualizer.plot_all_combined(df, params, analysis_results, output_dir=output_dir)

    elif mode == 'method_debug':
        visualizer.plot_gran_schwartz(analysis_results, params, output_dir=output_dir)
        visualizer.plot_gran_raw_with_search_diagnostic(analysis_results, params, output_dir=output_dir)
        visualizer.plot_schwartz_opt_with_search_diagnostic(analysis_results, params, output_dir=output_dir)

    else:
        print(f"Warning: unknown mode '{mode}', falling back to default plots")
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        visualizer.plot_gran_schwartz(analysis_results, params, output_dir=output_dir)

    # Step 6: Report (always generated, or make mode-dependent later)
    try:
        if args.verbose:
            print("Generating report...")
        # Mode-dependent CSV report
        csv_path = output_dir / "report.csv"
        if args.mode == 'method_development':
            reporter.generate_csv_report1(df, params, analysis_results, output_dir)
        elif args.mode == 'method_validation':
            reporter.generate_csv_report2(df, params, analysis_results, output_dir)
        elif args.mode == 'method_application':
            reporter.generate_csv_report3(df, params, analysis_results, output_dir)
        elif args.mode == 'method_debug':
            reporter.generate_csv_report4(df, params, analysis_results, output_dir)
        else:
            reporter.generate_csv_report(df, params, analysis_results, output_dir)  # fallback to original
    except Exception as e:
        print(f"Report error: {e}")
        # Non-fatal

if __name__ == "__main__":
    from pycallgraph2 import PyCallGraph, Config
    from pycallgraph2.output import GraphvizOutput
    args = parse_args()
    if args.profile:
        output = GraphvizOutput(output_file=str(Path(args.output_dir) / 'callgraph.svg'))
        with PyCallGraph(output=output):
            main()
    else:
        main()

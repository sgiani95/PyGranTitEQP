#!/usr/bin/env python3
"""
main.py: CLI orchestrator for GranTED titration pipeline.

Runs full workflow: load → preprocess → compute functions → analyze → visualize → report.
Supports method selection, plot embeds, batch stub, and profiling.
Usage: python main.py --data_file data.dat --titration_type weak_acid --embed_plots
       Or no args: Uses defaults (data.dat, ./output, weak_acid, both methods).
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Core modules
from data_io import load_single_file, validate_data
from preprocess import preprocess_pipeline
from gran_functions import compute_gran_functions
from analyzer import analyze_full_pipeline
from visualizer import visualize_all
from reporter import generate_report

# Profiling (optional)
try:
    from pycallgraph2 import PyCallGraph, Config
    from pycallgraph2.output import GraphvizOutput
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False
    print("Warning: pycallgraph2 not installed; skipping profiling.")


def load_config(args: argparse.Namespace, config_file: str) -> Dict[str, Any]:
    """Load and merge JSON config with args."""
    params = vars(args).copy()  # CLI to dict
    if config_file:
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            params.update(file_config)
            print(f"Loaded and merged config from {config_file}.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Config load failed ({e}); using CLI defaults.")
    return params


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute full pipeline with adaptations for refactored modules."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Step 1: Load and validate data
    print(f"Loading data from {args.data_file}...")
    df = load_single_file(args.data_file)
    if df is None:
        sys.exit(1)
    if not validate_data(df):
        print("Warning: Data validation issues; proceeding cautiously.")
    
    # Step 2: Preprocess (returns tuple)
    print("Preprocessing...")
    df, params = preprocess_pipeline(df, config_overrides=vars(args), config_file=args.config_file, interactive=args.interactive)
    
    # Step 3: Compute functions
    print("Computing Gran/Schwartz functions...")
    results = compute_gran_functions(df, params)
    
    # Step 4: Analyze (mutates results; method filter)
    methods = args.method.split(',') if args.method != 'both' else ['gran', 'schwartz']
    print(f"Analyzing methods: {methods}...")
    for m in methods:
        if m in results:
            from analyzer import analyze_gran  # Late import for modularity
            analyze_gran(results, params, m, optimize_k=args.optimize_k)
    
    # Step 5: Visualize (buffers if embed)
    embed_in_pdf = args.embed_plots
    buffers = visualize_all(df, params, results, str(output_dir), embed_in_pdf=embed_in_pdf)
    
    # Step 6: Report (pass buffers if embed)
    print("Generating report...")
    generate_report(df, params, results, str(output_dir), include_plots=args.embed_plots, buffers=buffers if embed_in_pdf else None)
    
    print(f"Pipeline complete! Outputs in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="GranTED: Gran/Schwartz Titration Analysis")
    parser.add_argument('--data_file', default='data.dat', help="Path to data file (default: data.dat)")
    parser.add_argument('--V', type=float, default=25.0, help="Initial volume (mL)")
    parser.add_argument('--C_B', type=float, default=0.1, help="Titrant concentration (M)")
    parser.add_argument('--titration_type', choices=['weak_acid', 'strong_acid', 'weak_base', 'strong_base'], default='weak_acid', help="Titration type")
    parser.add_argument('--method', choices=['gran', 'schwartz', 'both'], default='both', help="Method(s) to analyze")
    parser.add_argument('--output_dir', default='./output', help="Output directory")
    parser.add_argument('--config_file', help="Optional JSON config file")
    parser.add_argument('--embed_plots', action='store_true', help="Embed plots in PDF (chains visualizer)")
    parser.add_argument('--optimize_k', action='store_true', default=True, help="Run k5 optimization (default: True)")
    parser.add_argument('--r2_threshold', type=float, default=0.95, help="Min R² for zones")
    parser.add_argument('--savgol_window', type=int, default=5, help="SavGol window for derivatives")
    parser.add_argument('--case', choices=['default', 'case2', 'case3'], default='default', help="Zone fallback case")
    parser.add_argument('--interactive', action='store_true', default=False, help="Enable preprocess prompts")
    parser.add_argument('--no_profiling', action='store_true', help="Disable callgraph profiling")
    parser.add_argument('--batch_dir', help="Dir for batch (*.dat files); overrides --data_file")
    
    args = parser.parse_args()
    
    # Batch stub
    if args.batch_dir:
        batch_dir = Path(args.batch_dir)
        files = list(batch_dir.glob('*.dat'))
        if files:
            print(f"Batch mode: Processing {len(files)} files in {batch_dir}")
            for file in files:
                args.data_file = str(file)  # Temp override
                run_pipeline(args)
            return
        else:
            print("No .dat files in batch_dir; falling back to single.")
    
    # Load config if provided
    params = load_config(args, args.config_file)
    
    # Profiling wrapper
    if PROFILING_AVAILABLE and not args.no_profiling:
        config = Config(max_depth=3)
        graphviz = GraphvizOutput(output=Path(args.output_dir) / 'full_callgraph.svg')
        with PyCallGraph(output=graphviz, config=config):
            run_pipeline(args)
    else:
        run_pipeline(args)


if __name__ == "__main__":
    main()
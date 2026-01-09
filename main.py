# main.py: Entry Point for GranTED - Orchestrates Full Workflow
#TEST123
import argparse
import sys
from pathlib import Path
import json

# Local importsyes
from data_io import DataLoader
from preprocess import preprocess_pipeline
from gran_functions import compute_gran_functions
from analyzer import analyze_gran
from visualizer import visualize_all
from reporter import generate_report
from argparse import Namespace

# pycallgraph imports
from pycallgraph2 import PyCallGraph
from pycallgraph2 import Config
from pycallgraph2 import GlobbingFilter
from pycallgraph2.output import GraphvizOutput


def main():
    parser = argparse.ArgumentParser(description="GranTED Titration Analysis")
    parser.add_argument('--data_file', default='data.dat', help='Path to data file')
    parser.add_argument('--config_file', help='Path to JSON config file (optional)')
    parser.add_argument('--V', type=float, help='Initial volume offset (mL, overrides config)')
    parser.add_argument('--C_B', type=float, help='Titrant concentration (M, overrides config)')
    parser.add_argument('--titration_type', default=None, choices=['strong_acid', 'weak_acid', 'strong_base', 'weak_base'], help='Titration type (overrides config)')
    parser.add_argument('--output_dir', default='./output', help='Output directory for plots/reports')
    args = parser.parse_args()

    # Step 1: Load data
    loader = DataLoader()
    df = loader.load_single_file(args.data_file)
    if df is None:
        sys.exit(1)

    # Step 2: Preprocess (load config)
    config_overrides = {}
    if args.V is not None:
        config_overrides['V'] = args.V
    if args.C_B is not None:
        config_overrides['C_B'] = args.C_B
    if args.titration_type is not None:
        config_overrides['titration_type'] = args.titration_type
    
    # FIXED: Convert config_overrides to Namespace if it's a dict
    if isinstance(config_overrides, dict):
        config_overrides = Namespace(**config_overrides)

    df_processed, params = preprocess_pipeline(df, config_overrides, args.config_file)
    print("Preprocessed data ready. Final params:", params)

    # Step 3: Compute Gran functions
    gran_results = compute_gran_functions(df_processed, params)
    print("Gran functions computed.")

    # Step 4: Analyze (interval ID and k optimization)
    analysis_results = analyze_gran(df_processed, params)
    print("Analysis complete.")

    # Step 5: Visualize
    visualize_all(df_processed, params, analysis_results, args.output_dir)
    print("Visualizations generated.")

    # Step 6: Report
    generate_report(df_processed, params, analysis_results, args.output_dir)
    print(f"Full workflow complete. Results in {args.output_dir}")

if __name__ == "__main__":
    config = Config()
    config.trace_filter = GlobbingFilter(include=['analyzer.*', 'compare_gran_schwartz.*', 'data_io.*', 'dynamic_callgraph.*', 'gran_functions.*', 'GUI.*', 'main', 'preprocess.*', 'reporter.*', 'visualizer.*'])
    graphviz = GraphvizOutput(output_file='full_callgraph.svg', output_type='svg')
    with PyCallGraph(output=graphviz, config=config):
        main()
"""
modes.py - Orchestrates mode-specific behavior in GranTED.
Handles which plots to generate, which report variant to use,
and optional data trimming per mode.
"""

from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd

import visualizer
import reporter
import analyzer


def run_mode(
    mode: str,
    df: pd.DataFrame,
    params: Dict[str, Any],
    output_dir: Path,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Runs analysis and mode-specific visualization/reporting.
    Returns results + list of generated files.
    """
    if verbose:
        print(f"Executing mode: {mode}")

    # Optional: mode-specific trimming (customize per mode later)
    df_work = df.copy()  # default: full data
    # Example placeholder — add real trimming logic when needed
    # if mode in ['method_validation', 'method_application']:
    #     df_work = df_work[df_work['volume'] <= 10].copy()

    # Run core analysis on (possibly trimmed) data
    results = analyzer.analyze_gran(df_work, params, verbose=verbose)

    # Select and generate plots
    generated_files = []
    if mode == 'method_development':
        # Normal full-data plots (on the full dataset, not trimmed)
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.png')

        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.png')

        # Iterative trimming analysis (only for development mode)
        print("Development mode: iterative analysis (first 5 → full)")
        n_total = len(df)
        collected = {
            'n_points': [],
            'max_volume': [],
            'V_eq': [],
            'V_eq_unc': [],
            'optimal_k': [],
            'zone_points': [],
            'R2': []
        }

        for n in range(5, n_total + 1):
            df_trim = df.iloc[:n].copy()
            params_trim = params.copy()
            params_trim['volume_array'] = df_trim['volume'].values
            params_trim['potential_array'] = df_trim['potential'].values

            try:
                results_trim = analyzer.analyze_gran(df_trim, params_trim, verbose=False)
                opt_zone = results_trim.get('schwartz', {}).get('opt', {})

                collected['n_points'].append(n)
                collected['max_volume'].append(df_trim['volume'].max())
                collected['V_eq'].append(opt_zone.get('V_eq', np.nan))
                collected['V_eq_unc'].append(opt_zone.get('V_eq_unc', np.nan))
                collected['optimal_k'].append(opt_zone.get('k', np.nan))
                collected['zone_points'].append(
                    opt_zone.get('zone_end', 0) - opt_zone.get('zone_start', 0) + 1
                )
                collected['R2'].append(opt_zone.get('r2', np.nan))

                veq = opt_zone.get('V_eq', np.nan)
                unc = opt_zone.get('V_eq_unc', np.nan)
                print(f"  Trimmed to {n} points → V_eq = {veq:.3f} ± {unc:.3f}")

            except Exception as e:
                print(f"  Analysis failed for n={n}: {e}")
                for key in collected:
                    collected[key].append(np.nan)

        # Generate summary plot
        visualizer.plot_development_summary(collected, output_dir=output_dir, full_volume=params['volume_array'])

    elif mode == 'method_validation':
        visualizer.plot_all_combined(df_work, params, results, output_dir=output_dir)
        generated_files.append(output_dir / 'all_combined.png')

    elif mode == 'method_application':
        visualizer.plot_all_combined(df_work, params, results, output_dir=output_dir)
        generated_files.append(output_dir / 'all_combined.png')

    elif mode == 'method_debug':
        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.png')

        visualizer.plot_gran_raw_with_search_diagnostic(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_raw_search_diagnostic.png')

        visualizer.plot_schwartz_opt_with_search_diagnostic(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'schwartz_opt_search_diagnostic.png')

    else:
        print(f"Warning: unknown mode '{mode}', falling back to default plots")
        visualizer.plot_titration_curve(df_work, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.png')

    # Select and generate report variant
    csv_path = output_dir / 'report.csv'
    if mode == 'method_development':
        reporter.generate_csv_report1(df_work, params, results, output_dir)
    elif mode == 'method_validation':
        reporter.generate_csv_report2(df_work, params, results, output_dir)
    elif mode == 'method_application':
        reporter.generate_csv_report3(df_work, params, results, output_dir)
    elif mode == 'method_debug':
        reporter.generate_csv_report4(df_work, params, results, output_dir)
    else:
        reporter.generate_csv_report(results, csv_path)

    if verbose:
        print(f"Mode '{mode}' complete. Generated {len(generated_files)} plots.")

    return {
        'results': results,
        'generated_plots': generated_files,
        'csv_report': csv_path
    }

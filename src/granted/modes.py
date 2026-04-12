"""
modes.py - Orchestrates mode-specific behavior in GranTED.
Handles plots, reports, trimming, and earliest acceptable point detection.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
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
    verbose: bool = False,
    r2_min: float = 0.9995,
    unc_max: float = 0.01,
    veq_tolerance: float = 0.02,
    stability_window: int = 3,
    trim_forward: bool = False
) -> Dict[str, Any]:
    """
    Main orchestrator for mode-specific execution.
    """
    if verbose:
        print(f"Executing mode: {mode} | trim_forward={trim_forward}")

    df_work = df.copy()

    # Run core analysis on full data first (to get reference V_eq)
    results = analyzer.analyze_gran(df_work, params, verbose=verbose)

    generated_files = []

    if mode == 'method_development':
        # Normal full-data plots
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.png')

        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.png')

        # Iterative trimming + detection
        print("Development mode: performing backward trimming analysis...")
        collected, earliest_n, reference_veq = _trimming_analysis(
            df, params,
            r2_min=r2_min,
            unc_max=unc_max,
            veq_tolerance=veq_tolerance,
            stability_window=stability_window,
            trim_forward=trim_forward,
            verbose=verbose
        )

        visualizer.plot_development_summary(
            collected, 
            output_dir=output_dir, 
            full_volume=params['volume_array'],
            earliest_n=earliest_n,
            reference_veq=reference_veq,      # now properly passed
            r2_min=r2_min,
            unc_max=unc_max,
            veq_tolerance=veq_tolerance
        )
        generated_files.append(output_dir / 'development_convergence_volume.png')

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
        print(f"Warning: unknown mode '{mode}', falling back to default")
        visualizer.plot_titration_curve(df_work, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.png')

    # Report selection
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

    return {
        'results': results,
        'generated_plots': generated_files,
        'csv_report': csv_path,
        'earliest_acceptable_n': earliest_n if mode == 'method_development' else None
    }

def _trimming_analysis(
    df: pd.DataFrame,
    params: Dict[str, Any],
    r2_min: float,
    unc_max: float,
    veq_tolerance: float,
    stability_window: int,
    trim_forward: bool,
    verbose: bool
) -> Tuple[Dict[str, list], int | None, float | None]:
    """
    Performs trimming analysis and detects earliest acceptable point.
    Backward trimming is default.
    """
    n_total = len(df)
    collected = {
        'n_points': [], 'max_volume': [], 'V_eq': [], 'V_eq_unc': [],
        'optimal_k': [], 'zone_points': [], 'R2': []
    }

    reference_veq = None
    earliest_n = None
    consecutive_bad = 0

    if trim_forward:
        range_iter = range(5, n_total + 1)
    else:
        range_iter = range(n_total, 4, -1)   # backward: full → 5

    for n in range_iter:
        df_trim = df.iloc[:n].copy()
        params_trim = params.copy()
        params_trim['volume_array'] = df_trim['volume'].values
        params_trim['potential_array'] = df_trim['potential'].values

        try:
            results_trim = analyzer.analyze_gran(df_trim, params_trim, verbose=False)
            opt_zone = results_trim.get('schwartz', {}).get('opt', {})

            veq = opt_zone.get('V_eq', np.nan)
            unc = opt_zone.get('V_eq_unc', np.nan)
            r2 = opt_zone.get('r2', np.nan)
            k = opt_zone.get('k', np.nan)
            zone_n = opt_zone.get('zone_end', 0) - opt_zone.get('zone_start', 0) + 1

            collected['n_points'].append(n)
            collected['max_volume'].append(df_trim['volume'].max())
            collected['V_eq'].append(veq)
            collected['V_eq_unc'].append(unc)
            collected['optimal_k'].append(k)
            collected['zone_points'].append(zone_n)
            collected['R2'].append(r2)

            # Set reference from full dataset
            if reference_veq is None and not np.isnan(veq):
                reference_veq = veq

            # Check if ALL three conditions are satisfied
            if reference_veq is not None:
                is_good = (
                    r2 >= r2_min and
                    unc <= unc_max and
                    abs(veq - reference_veq) <= veq_tolerance and
                    not np.isnan(veq) and not np.isnan(unc)
                )

                if is_good:
                    consecutive_bad = 0
                else:
                    consecutive_bad += 1

                # Trigger as soon as ANY condition fails for stability_window consecutive steps
                if consecutive_bad >= stability_window and earliest_n is None:
                    earliest_n = n + stability_window  # last good point before the bad streak
                    if verbose:
                        print(f"→ Earliest acceptable point detected at n={earliest_n} "
                              f"(V_eq ≈ {reference_veq:.3f}, bad streak of {stability_window} started)")

            if verbose:
                print(f"  Trimmed to {n} points → V_eq = {veq:.3f} ± {unc:.3f} (R²={r2:.4f})")

        except Exception as e:
            print(f"  Analysis failed for n={n}: {e}")
            for key in collected:
                collected[key].append(np.nan)

    return collected, earliest_n, reference_veq

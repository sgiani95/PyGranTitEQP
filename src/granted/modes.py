"""
modes.py - Orchestrates mode-specific behavior in GranTED.
Handles plots, reports, trimming, and earliest acceptable point detection.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import sys

from granted import visualizer
from granted import reporter
from granted import analyzer


def run_mode(
    mode: str,
    df: pd.DataFrame,
    params: Dict[str, Any],
    output_dir: Path,
    verbose: bool = False,
    r2_min: float = 0.99,
    unc_max: float = 0.05,
    veq_tolerance: float = 0.1,
    stability_window: int = 3,
    trim_forward: bool = False,
    vopt: float | None = None   # New: for method_validation
) -> Dict[str, Any]:
    """
    Main orchestrator for mode-specific execution.
    Single if-elif structure for clarity.
    """
    if verbose:
        print(f"Executing mode: {mode}")

    df_work = df.copy()

    # Run core analysis on full data (common to most modes)
    results = analyzer.analyze_gran(df_work, params, verbose=verbose)

    generated_files = []

    if mode == 'method_development':
        # Normal full-data plots
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.pdf')

        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.pdf')

        # Backward trimming analysis (Gran + Schwartz on every trim - as per your revert)
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

        # Development summary plot
        visualizer.plot_development_summary(
            collected, output_dir=output_dir, 
            full_volume=params['volume_array'],
            earliest_n=earliest_n,
            reference_veq=reference_veq,
            r2_min=r2_min,
            unc_max=unc_max,
            veq_tolerance=veq_tolerance
        )
        generated_files.append(output_dir / 'development_convergence_volume.pdf')

        # Special report
        reporter.generate_csv_report_development(
            df_work, params, results, collected, earliest_n, reference_veq, output_dir
        )

    elif mode == 'method_validation':
        if vopt is None:
            print("Error: --vopt is required for method_validation mode.")
            sys.exit(1)

        print(f"Method Validation: Using V_opt = {vopt:.3f} mL")

        # Full analysis on new dataset
        results_full = analyzer.analyze_gran(df_work, params, verbose=verbose)

        # Trimmed analysis to V_opt
        df_trim = df[df['volume'] <= vopt].copy()
        params_trim = params.copy()
        params_trim['volume_array'] = df_trim['volume'].values
        params_trim['potential_array'] = df_trim['potential'].values

        results_vopt = analyzer.analyze_gran(df_trim, params_trim, verbose=verbose)

        # Generate validation report
        reporter.generate_csv_report_validation(
            df_work, params, results_full, results_vopt, vopt, output_dir
        )

    elif mode == 'method_application':
        print("Method Application: Analyzing already trimmed data up to V_opt")

        # Single Gran + Schwartz analysis on the provided (trimmed) dataset
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.pdf')

        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.pdf')

        # Standard report (no special Vopt handling)
        reporter.generate_csv_report_application(df_work, params, results, output_dir)

    elif mode == 'method_debug':
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.pdf')
        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.pdf')
        visualizer.plot_all_combined(df, params, results, output_dir=output_dir)
        generated_files.append(output_dir / 'all_combined.pdf')

        # Add more debug plots as needed
        reporter.generate_csv_report4(df_work, params, results, output_dir)

    else:
        print(f"Warning: unknown mode '{mode}', falling back to development")
        # fallback to development behavior
        visualizer.plot_titration_curve(df, params, output_dir=output_dir)
        generated_files.append(output_dir / 'titration_curve.pdf')
        visualizer.plot_gran_schwartz(results, params, output_dir=output_dir)
        generated_files.append(output_dir / 'gran_schwartz.pdf')

    return {
        'results': results,
        'generated_plots': generated_files,
        'csv_report': output_dir / 'report.csv'
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
        range_iter = range(n_total, 4, -1)   # backward: full, 5

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

            # Store zone boundaries for report
            collected.setdefault('zone_start', []).append(opt_zone.get('zone_start', None))
            collected.setdefault('zone_end', []).append(opt_zone.get('zone_end', None))

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
                        print(f" Earliest acceptable point detected at n={earliest_n} "
                              f"(V_eq ≈ {reference_veq:.3f}, bad streak of {stability_window} started)")

            if verbose:
                print(f"  Trimmed to {n} points → V_eq = {veq:.3f} ± {unc:.3f} (R²={r2:.4f})")

        except Exception as e:
            print(f"  Analysis failed for n={n}: {e}")
            for key in collected:
                collected[key].append(np.nan)

    return collected, earliest_n, reference_veq

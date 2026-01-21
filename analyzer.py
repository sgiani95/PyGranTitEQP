# analyzer.py: Module 4 for GranTED - Interval Identification and Parameter Optimization

#######################
# Core Functionality: #
#######################
#
# Interval Identification: Automatically detects "the Zone" linear region in the Gran function (g1) using derivative analysis + rolling R² maximization,
# targeting the steep negative-slope part for reliable fitting. Includes optional SavGol smoothing based on raw derivative noise check and segmented plateau detection for robustness.
#
# Parameter Optimization: Tunes k5 to maximize R² in the identified interval, with optional extension to include more points while maintaining linearity. Computes and stores both unoptimized (k5=0) and optimized results for comparison.
#
# Analysis Orchestration: Integrates Gran computation, interval finding, and optimization, outputting results (interval indices, fit params, R²) for both cases
# for visualizer.py and reporter.py.
#
# Output: Dict with {'interval': (start, end), 'unoptimized': {...}, 'optimized': {...}, 'g1': array}, ready for plotting/reporting.

import numpy as np
import pandas as pd
from scipy.stats import linregress
from scipy.signal import savgol_filter
from gran_functions import compute_gran_functions
from scipy.optimize import minimize_scalar

def _compute_r2(g1_smooth, volume, start, end):
    """Helper: Compute R² and fit for a segment."""
    if end - start < 2:
        return 0.0, 0.0, 0.0
    slope, intercept, r_value, _, _ = linregress(volume[start:end], g1_smooth[start:end])
    return r_value**2, slope, intercept

def identify_linear_interval(g1, volume, min_points=5, window_size=5, noise_threshold=0.001, 
                             var_threshold_rel=0.1, min_r2=0.95):
    """
    Identify "the Zone" using derivative-based segmentation and ranking.
    Handles Cases 1-3 via plateau detection in negative dg1.
    """
    # Step 1: Compute dg1 (with optional smoothing)
    dg1_raw = np.gradient(g1, volume)
    std_dg1 = np.std(dg1_raw)
    if std_dg1 > noise_threshold:
        print(f"High noise (std_dg1={std_dg1:.2e} > {noise_threshold}). Smoothing.")
        g1_smooth = savgol_filter(g1, window_length=window_size, polyorder=2)
        dg1 = np.gradient(g1_smooth, volume)
    else:
        print(f"Low noise (std_dg1={std_dg1:.2e} <= {noise_threshold}). No smoothing.")
        g1_smooth = g1
        dg1 = dg1_raw
    
    # Focus on negative dg1 region
    neg_mask = dg1 < 0
    if not np.any(neg_mask):
        print("Warning: No negative derivative. Using full range.")
        return 0, len(g1) - 1, 0.0
    
    dg1_neg = dg1[neg_mask]
    vol_neg_idx = np.where(neg_mask)[0]
    
    # Step 2: Segment into candidate plateaus via sliding-window variance
    candidates = []
    win_sizes = range(max(3, min_points//2), min(15, len(dg1_neg)//2) + 1)
    for win_len in win_sizes:
        for i in range(len(dg1_neg) - win_len + 1):
            seg_dg1 = dg1_neg[i:i+win_len]
            mean_dg = np.mean(seg_dg1)
            var_dg = np.var(seg_dg1)
            if mean_dg < 0 and var_dg < var_threshold_rel * abs(mean_dg):
                orig_start = vol_neg_idx[i]
                orig_end = vol_neg_idx[i + win_len - 1] + 1
                candidates.append({
                    'orig_start': orig_start,
                    'orig_end': orig_end,
                    'length': win_len,
                    'mean_dg': mean_dg,
                    'var_dg': var_dg
                })
    
    if not candidates:
        print("No low-var negative segments found. Falling back to full negative region.")
        full_start = vol_neg_idx[0]
        full_end = vol_neg_idx[-1] + 1
        _, _, r2_full = _compute_r2(g1_smooth, volume, full_start, full_end)
        return full_start, full_end, r2_full
    
    # Step 3: Rank candidates by R², length, |mean_dg|
    scored = []
    for cand in candidates:
        r2, slope, intercept = _compute_r2(g1_smooth, volume, cand['orig_start'], cand['orig_end'])
        if r2 >= min_r2:
            score = r2 * 100 + (cand['length'] / len(g1)) * 10 + abs(cand['mean_dg']) * 0.1
            scored.append((cand, score, r2))
    
    if not scored:
        # Fallback: Score all by composite even if R² < min_r2
        fallback_scored = []
        for cand in candidates:
            r2, _, _ = _compute_r2(g1_smooth, volume, cand['orig_start'], cand['orig_end'])
            score = r2 * 100 + (cand['length'] / len(g1)) * 10 + abs(cand['mean_dg']) * 0.1
            fallback_scored.append((cand, score, r2))
        scored = fallback_scored
    
    best_cand, best_score, best_r2 = max(scored, key=lambda x: x[1])
    start_idx, end_idx = best_cand['orig_start'], best_cand['orig_end']
    
    # Case labeling (heuristic)
    case = "Case 3"  # Default gradual
    if start_idx > 0:
        pre_mean = np.mean(dg1[:start_idx])
        pre_std = np.std(dg1[:start_idx])
        if pre_mean > 0:
            case = "Case 1"
        elif pre_std < 0.01 * abs(pre_mean):
            case = "Case 2"
    
    print(f"Identified 'the Zone': indices {start_idx}-{end_idx}, R²={best_r2:.3f} (Case: {case}, Score: {best_score:.2f})")
    return start_idx, end_idx, best_r2

def _compute_fit(df, start, end, gran_func, k5=0.0):
    """
    Compute fit, R², and V_eq for a zone with given k5, using gran_func callable.
    """
    volume = df['volume'].iloc[start:end].values
    potential = df['potential'].iloc[start:end].values
    pH = 7 - (potential / 59.16)
    y = gran_func(volume, pH, k5)  # Use callable
    slope, intercept, r_value, _, _ = linregress(volume, y)
    r2 = r_value**2
    veq = -intercept / slope if slope != 0 else np.nan
    return {'r2': r2, 'fit': (slope, intercept), 'veq': veq}

def _optimize_single_zone(df, start, end, gran_func, k_bounds):
    """
    Optimize k5 for a fixed zone using gran_func callable.
    """
    volume = df['volume'].iloc[start:end].values
    potential = df['potential'].iloc[start:end].values
    pH = 7 - (potential / 59.16)
    
    def negative_r2(k5):
        y = gran_func(volume, pH, k5)  # Use callable
        slope, intercept, r_value, _, _ = linregress(volume, y)
        return -r_value**2
    
    result = minimize_scalar(negative_r2, bounds=k_bounds, method='bounded')
    best_k5 = result.x
    max_r2 = -result.fun
    y_opt = gran_func(volume, pH, best_k5)
    slope, intercept, _, _, _ = linregress(volume, y_opt)
    return {'best_k5': best_k5, 'best_r2': max_r2, 'fit': (slope, intercept)}

def analyze_gran(df, params, use_segmented=True, use_extension=True):
    """
    Main analysis: Compute Gran, identify raw interval, fit raw, then optimize/extend for opt Zone.
    Returns results with separate raw/opt Zones for comparison.
    """
    # Compute Gran functions (weakacid_g1 focus, with k5=0 default)
    gran_results = compute_gran_functions(df, params)
    g1 = gran_results['g1']  # General g1 array (weak_acid_g1 by default)
    gran_func = gran_results['gran_func']  # Extract callable for optimization
    params['volume'] = df['volume'].values  # Ensure volume in params for visualizer

    # Identify initial interval (on raw g1)
    if use_segmented:
        start_idx, end_idx, _ = identify_linear_interval(g1, params['volume'])
    else:
        start_idx, end_idx, _ = _identify_linear_original(g1, params['volume'])

    initial_interval = (start_idx, end_idx)
    
    # Raw Zone: Fit on initial interval (no opt/extension)
    raw_zone = _compute_fit(df, start_idx, end_idx, gran_func, k5=0.0)
    raw_zone['start'] = start_idx
    raw_zone['end'] = end_idx
    raw_zone['num_points'] = end_idx - start_idx
    
    print(f"Raw Zone (initial): indices {start_idx}-{end_idx}, R²={raw_zone['r2']:.4f}, V_eq={raw_zone['veq']:.3f} mL over {raw_zone['num_points']} points")

    # Opt k5 on raw Zone (no extension yet)
    k_bounds = (-10, 10)  # Default bounds
    opt_k5 = _optimize_single_zone(df, start_idx, end_idx, gran_func, k_bounds)['best_k5']
    
    # Recompute g1_opt and re-detect Zone on it
    pH_full = 7 - (df['potential'].values / 59.16)
    g1_opt = gran_func(params['volume'], pH_full, opt_k5)
    if use_segmented:
        opt_start, opt_end, opt_interval_r2 = identify_linear_interval(g1_opt, params['volume'])
    else:
        opt_start, opt_end, opt_interval_r2 = _identify_linear_original(g1_opt, params['volume'])
    
    # Opt fit on re-detected Zone
    opt_zone = _compute_fit(df, opt_start, opt_end, gran_func, k5=opt_k5)
    opt_zone['k5'] = opt_k5
    opt_zone['start'] = opt_start
    opt_zone['end'] = opt_end
    opt_zone['num_points'] = opt_end - opt_start

    # Fallback if opt Zone smaller than raw (prevent shrinkage)
    if opt_zone['num_points'] < raw_zone['num_points']:
        opt_start, opt_end = raw_zone['start'], raw_zone['end']
        opt_zone = _compute_fit(df, opt_start, opt_end, gran_func, k5=opt_k5)
        opt_zone['k5'] = opt_k5  # Ensure k5 in fallback
        opt_zone['start'] = opt_start
        opt_zone['end'] = opt_end
        opt_zone['num_points'] = opt_end - opt_start
        print(f"Opt fallback to raw Zone (to avoid shrinkage): R²={opt_zone['r2']:.4f}, points={opt_zone['num_points']}")

    print(f"Opt Zone (final): k5={opt_k5:.3f}, R²={opt_zone['r2']:.4f}, V_eq={opt_zone['veq']:.3f} mL over {opt_zone['num_points']} points")

    results = {
        'raw_zone': raw_zone,  # Initial raw
        'opt_zone': opt_zone,  # Re-detected or fallback opt
        'g1': g1,  # Raw g1 for plotting
        'g1_opt': g1_opt,  # Opt g1 for plotting
        'interval_r2': raw_zone['r2'],  # Legacy
    }

    print("Gran analysis complete with separate raw/opt Zones.")
    return results

def _identify_linear_original(g1, volume, min_points=5, window_size=5):
    """
    Original non-segmented interval identification (fallback).
    """
    dg1_raw = np.gradient(g1, volume)
    std_dg1 = np.std(dg1_raw)
    if std_dg1 > 0.001:
        g1_smooth = savgol_filter(g1, window_length=window_size, polyorder=2)
        dg1 = np.gradient(g1_smooth, volume)
    else:
        g1_smooth = g1
        dg1 = dg1_raw
    negative_start = np.where(dg1 < 0)[0]
    if len(negative_start) == 0:
        return 0, len(g1) - 1, 0.0
    start_idx = negative_start[0]
    min_deriv_idx = start_idx + np.argmin(dg1[start_idx:])
    best_r2 = 0.0
    best_start, best_end = start_idx, min_deriv_idx
    for test_start in range(start_idx, min_deriv_idx - min_points + 1):
        for test_end in range(test_start + min_points, min(min_deriv_idx + 10, len(g1))):
            if test_end - test_start < min_points:
                continue
            slope, intercept, r_value, _, _ = linregress(volume[test_start:test_end], g1_smooth[test_start:test_end])
            r2 = r_value**2
            if r2 > best_r2:
                best_r2 = r2
                best_start, best_end = test_start, test_end
    print(f"Original method: indices {best_start}-{best_end}, R²={best_r2:.3f}")
    return best_start, best_end, best_r2

# Example usage (for testing)
if __name__ == "__main__":
    df = pd.read_csv('data.dat', names=['volume', 'potential'], sep='\s+')
    params = {'V': 25.0}
    results = analyze_gran(df, params)
    print("Results:", results)
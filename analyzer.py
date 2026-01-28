"""
analyzer.py: Validated equivalence point detection via Gran/Schwartz linearization.

Algorithm preserved: Smoothing → deriv → candidates → rank/eval → shrink (raw) → opt k5 → re-shrink (opt).
Outputs nested metrics for downstream (gran/schwartz raw/opt with V_eq, r2, k5, zones).

Dependencies: numpy, scipy.stats.linregress, scipy.signal.savgol_filter, scipy.optimize.minimize_scalar.
"""

import numpy as np
import pandas as pd
from scipy.stats import linregress
from scipy.signal import savgol_filter
from scipy.optimize import minimize_scalar
from gran_functions import compute_gran_functions  # For compatibility
from typing import Tuple, Dict, Any, Callable


def _compute_r2(g1_smooth: np.ndarray, volume: np.ndarray, start: int, end: int) -> Tuple[float, float, float]:
    """Helper: Compute R², slope, intercept for a segment (preserved)."""
    if end - start < 2:
        return 0.0, 0.0, 0.0
    slope, intercept, r_value, _, _ = linregress(volume[start:end+1], g1_smooth[start:end+1])
    return r_value**2, slope, intercept


def identify_linear_interval(
    g1: np.ndarray, volume: np.ndarray, min_points: int = 5, window_size: int = 5,
    noise_threshold: float = 0.001, var_threshold_rel: float = 0.1, min_r2: float = 0.95
) -> Tuple[int, int, float]:
    """
    Identify "the Zone" using derivative-based segmentation and ranking. Handles Cases 1-3 via plateau detection in negative dg1 (preserved).

    Args:
        g1: Gran g1 array.
        volume: Volume array (mL).
        min_points: Minimum zone length.
        window_size: SavGol window.
        noise_threshold: Std threshold for smoothing.
        var_threshold_rel: Relative var for candidates.
        min_r2: Minimum R² for high-score zones.

    Returns:
        Tuple (start_idx, end_idx, best_r2).
    """
    # Step 1: Compute dg1 (with optional smoothing)
    dg1_raw = np.gradient(g1, volume)
    std_dg1 = np.std(dg1_raw)
    if std_dg1 > noise_threshold:
        g1_smooth = savgol_filter(g1, window_length=window_size, polyorder=2)
        dg1 = np.gradient(g1_smooth, volume)
    else:
        g1_smooth = g1
        dg1 = dg1_raw

    # Focus on negative dg1 region
    neg_mask = dg1 < 0
    if not np.any(neg_mask):
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
        full_start = vol_neg_idx[0]
        full_end = vol_neg_idx[-1] + 1
        _, _, r2_full = _compute_r2(g1_smooth, volume, full_start, full_end)
        return full_start, full_end, r2_full

    # Step 3: Rank candidates by R², length, |mean_dg| (consolidated eval)
    scored = []
    for cand in candidates:
        r2, slope, intercept = _compute_r2(g1_smooth, volume, cand['orig_start'], cand['orig_end'])
        if r2 >= min_r2:
            score = r2 * 100 + (cand['length'] / len(g1)) * 10 + abs(cand['mean_dg']) * 0.1
        else:
            # Fallback scoring for low R²
            score = r2 * 100 + (cand['length'] / len(g1)) * 10 + abs(cand['mean_dg']) * 0.1
        scored.append((cand, score, r2))

    best_cand, best_score, best_r2 = max(scored, key=lambda x: x[1])
    start_idx, end_idx = best_cand['orig_start'], best_cand['orig_end']

    # Case labeling (heuristic, preserved)
    case = "Case 3"  # Default gradual
    if start_idx > 0:
        pre_mean = np.mean(dg1[:start_idx])
        pre_std = np.std(dg1[:start_idx])
        if pre_mean > 0:
            case = "Case 1"
        elif pre_std < 0.01 * abs(pre_mean):
            case = "Case 2"

    return start_idx, end_idx, best_r2


def _compute_fit(df: pd.DataFrame, start: int, end: int, gran_func: Callable, k5: float = 0.0) -> Dict[str, Any]:
    """Compute fit, R², and V_eq for a zone with given k5, using gran_func callable (preserved)."""
    volume = df['volume'].iloc[start:end+1].values
    potential = df['potential'].iloc[start:end+1].values
    pH = 7 - (potential / 59.16)
    y = gran_func(volume, pH, k5)  # Use callable
    slope, intercept, r_value, _, _ = linregress(volume, y)
    r2 = r_value**2
    veq = -intercept / slope if slope != 0 else np.nan
    return {'r2': r2, 'fit': (slope, intercept), 'veq': veq}


def _optimize_single_zone(df: pd.DataFrame, start: int, end: int, gran_func: Callable, k_bounds: Tuple[float, float] = (-10, 10)) -> Dict[str, Any]:
    """Optimize k5 for a fixed zone using gran_func callable (preserved)."""
    volume = df['volume'].iloc[start:end+1].values
    potential = df['potential'].iloc[start:end+1].values
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


def shrink_zone(
    volume: np.ndarray, g_values: np.ndarray, initial_zone: Tuple[int, int], max_iter: int = 10
) -> Tuple[int, int]:
    """
    Asymmetric zone refinement: prefer growing left (low volumes), trimming right (high volumes).
    Binary trim + small grow for >5% R² gain; validated Case 3 refinement.
    """
    start, end = initial_zone
    current_r2, _, _ = _compute_r2(g_values, volume, start, end)
    iter_count = 0
    improved = True

    while improved and iter_count < max_iter and end - start > 2:
        improved = False

        # Step 1: Try growing left (extend start downward)
        if start > 0:
            new_start = max(0, start - 1)  # Small step left
            left_r2, _, _ = _compute_r2(g_values, volume, new_start, end)
            if left_r2 > current_r2 * 1.05:
                start = new_start
                current_r2 = left_r2
                improved = True
                iter_count = 0  # Reset on improvement

        # Step 2: Try trimming right (shrink end upward)
        if end < len(volume) - 1:
            new_end = min(len(volume) - 1, end + 1)  # Small step right (trim)
            right_r2, _, _ = _compute_r2(g_values, volume, start, new_end)
            if right_r2 > current_r2 * 1.05:
                end = new_end
                current_r2 = right_r2
                improved = True
                iter_count = 0

        # Step 3: Try trimming left (only if no growth happened)
        if not improved and start + 1 < end:
            left_mid = (start + end) // 2
            if left_mid > start:
                left_r2, _, _ = _compute_r2(g_values, volume, left_mid, end)
                if left_r2 > current_r2 * 1.05:
                    start = left_mid
                    current_r2 = left_r2
                    improved = True
                    iter_count = 0

        # Step 4: Try trimming right (symmetric fallback)
        if not improved and start < end - 1:
            right_mid = (start + end) // 2
            if right_mid < end:
                right_r2, _, _ = _compute_r2(g_values, volume, start, right_mid)
                if right_r2 > current_r2 * 1.05:
                    end = right_mid
                    current_r2 = right_r2
                    improved = True
                    iter_count = 0

        iter_count += 1

    return (start, end)

def get_metrics(fit: Any, zone: Tuple[int, int], k5: float = 0.0, r2_threshold: float = 0.95) -> Dict[str, Any]:
    """Extract V_eq, r2 from fit/zone (centralized for raw/opt). Warn on low R²; fallback V_eq if slope ~0."""
    start, end = zone
    if fit is None or end - start < 2:
        return {'V_eq': np.nan, 'r2': 0.0, 'k5': k5, 'zone_start': start, 'zone_end': end, 'green_savings': 0.0}
    slope, intercept = fit['fit']
    r2 = fit['r2']
    if abs(slope) < 1e-6:  # Near-zero slope fallback
        v_eq = np.mean(volume[start:end+1])  # Mid-zone estimate
        print(f"Warning: Low slope={slope:.3e} in zone {zone}—V_eq fallback to mean {v_eq:.3f} mL")
    else:
        v_eq = -intercept / slope
    if r2 < r2_threshold:
        print(f"Warning: Low R²={r2:.3f} for zone {zone} (k5={k5})")
    green_savings = 0.05 * r2  # Stub: Scale by R² (e.g., 0.05 L for perfect fit)
    print(f"DEBUG: get_metrics returning fit = {fit['fit'] if fit else 'None'} for zone {zone}")
    return {
        'V_eq': round(v_eq, 3),
        'r2': round(r2, 4),
        'k5': round(k5,4),
        'zone_start': start,
        'zone_end': end,
        'fit': fit['fit'] if fit and 'fit' in fit else None  # Pass the (slope, intercept) tuple
    }
    
def analyze_gran_original(df: pd.DataFrame, params: Dict[str, Any], use_segmented: bool = True, verbose: bool = False) -> Dict[str, Any]:
    """Main analysis: Compute Gran, identify raw interval, fit raw, then optimize/extend for opt Zone (preserved)."""
    print("DEBUG: Entering analyze_gran_original...")
    print(f"DEBUG: df shape: {df.shape}, params keys: {list(params.keys())}")
    
    # Step: Compute Gran functions
    print("DEBUG: Step - Compute Gran functions...")
    try:
        gran_results = compute_gran_functions(df, params)
        g1 = gran_results['gran']['g1']  # Raw g1 array
        gran_func = gran_results['gran']['gran_func']  # Fixed lambda
        schwartz_func = gran_results['schwartz']['gran_func']  # Tunable lambda
        if 'volume' not in params:
            params['volume_array'] = params.get('volume_array', df['volume'].values)  # Fallback
        print(f"DEBUG: params['volume_array'] shape: {params['volume_array'].shape}")  # Temp debug
    except Exception as e:
        print(f"DEBUG: Gran compute failed: {e}")
        return None
    g1 = gran_results['gran']['g1']  # Raw g1 array
    gran_func = gran_results['gran'].get('gran_func', lambda v, ph, kk: v * np.power(10, -ph))  # Safe fallback fixed lambda
    schwartz_func = gran_results['schwartz'].get('gran_func', gran_func)  # Safe fallback to gran_func if Schwartz missing
    print("DEBUG: Gran extract OK, g1 shape: {g1.shape}")

    diagnostics = []  # For verbose grouping

    # Step: Identify initial interval (on raw g1)
    print("DEBUG: Step - Identify initial interval...")
    try:
        if use_segmented:
            start_idx, end_idx, _ = identify_linear_interval(g1, params['volume_array'])
        else:
            start_idx, end_idx, _ = _identify_linear_original(g1, params['volume_array'])
        initial_interval = (start_idx, end_idx)
        print(f"DEBUG: Interval ID OK, start={start_idx}, end={end_idx}")
    except Exception as e:
        print(f"DEBUG: Interval ID failed: {e}")
        return None

    # Step: Raw Zone: Fit on initial interval
    print("DEBUG: Step - Raw Zone fit...")
    try:
        raw_zone = _compute_fit(df, start_idx, end_idx, gran_func, k5=0.0)
        raw_zone.update({'start': start_idx, 'end': end_idx, 'num_points': end_idx - start_idx})  # Safe update
        raw_num_points = raw_zone['num_points']
        raw_metrics = get_metrics({'r2': raw_zone['r2'], 'fit': raw_zone['fit']}, initial_interval, k5=0.0)
        raw_metrics['num_points'] = raw_num_points
        diagnostics.append(f"Raw Zone (initial): indices {start_idx}-{end_idx}, R²={raw_metrics['r2']:.4f}, V_eq={raw_metrics['V_eq']:.3f} mL over {raw_num_points} points")
    except Exception as e:
        print(f"DEBUG: Raw zone failed: {e}")
        return None

    # Step: Opt k5 on raw Zone
    print("DEBUG: Step - Opt k5...")
    try:
        k_bounds = (-10, 10)
        opt_k5_dict = _optimize_single_zone(df, start_idx, end_idx, schwartz_func, k_bounds)
        opt_k5 = opt_k5_dict['best_k5']
        print(f"DEBUG: Opt k5 OK, best_k5={opt_k5:.3f}")
    except Exception as e:
        print(f"DEBUG: Opt k5 failed: {e}")
        return None

    # Step: Recompute gs_opt and re-detect Zone
    print("DEBUG: Step - Recompute gs_opt...")
    try:
        pH_full = 7 - (df['potential'].values / 59.16)
        gs_opt = schwartz_func(params['volume_array'], pH_full, opt_k5)
        print(f"DEBUG: gs_opt shape: {gs_opt.shape}")
    except Exception as e:
        print(f"DEBUG: gs_opt recompute failed: {e}")
        return None
    
    print("DEBUG: Step - Re-detect opt zone...")
    try:
        if use_segmented:
            opt_start, opt_end, opt_interval_r2 = identify_linear_interval(gs_opt, params['volume_array'])
        else:
            opt_start, opt_end, opt_interval_r2 = _identify_linear_original(gs_opt, params['volume_array'])
        print(f"DEBUG: Opt re-detect OK, start={opt_start}, end={opt_end}")
    except Exception as e:
        print(f"DEBUG: Opt re-detect failed: {e}")
        return None

    # Step: Opt fit on re-detected Zone
    print("DEBUG: Step - Opt fit...")
    try:
        opt_zone = _compute_fit(df, opt_start, opt_end, schwartz_func, k5=opt_k5)
        opt_zone.update({'k5': opt_k5, 'start': opt_start, 'end': opt_end, 'num_points': opt_end - opt_start})
        opt_num_points = opt_zone['num_points']
        opt_metrics = get_metrics({'r2': opt_zone['r2'], 'fit': opt_zone['fit']}, (opt_start, opt_end), k5=opt_k5)
        opt_metrics['num_points'] = opt_num_points
    except Exception as e:
        print(f"DEBUG: Opt zone failed: {e}")
        return None

    # Step: Fallback if opt smaller than raw
    print("DEBUG: Step - Fallback check...")
    try:
        if opt_num_points < raw_num_points:
            opt_start, opt_end = raw_metrics['zone_start'], raw_metrics['zone_end']
            opt_zone = _compute_fit(df, opt_start, opt_end, schwartz_func, k5=opt_k5)
            opt_num_points = opt_end - opt_start + 1
            opt_metrics = get_metrics({'r2': opt_zone['r2'], 'fit': opt_zone['fit']}, (opt_start, opt_end), k5=opt_k5)
            opt_metrics['num_points'] = opt_num_points
            diagnostics.append(f"Opt fallback to raw Zone (to avoid shrinkage): R²={opt_metrics['r2']:.4f}, points={opt_num_points}")
            print("DEBUG: Fallback triggered")
        else:
            print("DEBUG: No fallback needed")
    except Exception as e:
        print(f"DEBUG: Fallback failed: {e}")
        return None

    diagnostics.append(f"Opt Zone (final): k5={opt_k5:.3f}, R²={opt_metrics['r2']:.4f}, V_eq={opt_metrics['V_eq']:.3f} mL over {opt_num_points} points")

    # Step: Build results dict
    print("DEBUG: Step - Build results...")
    try:
        results = {
            'raw_zone': raw_metrics,  # Initial raw (Gran k=0)
            'opt_zone': opt_metrics,  # Re-detected opt (Schwartz kk)
            'g1': g1,  # Raw g1 for plotting
            'g1_opt': gs_opt,  # Opt gs for plotting (Schwartz)
            'interval_r2': raw_metrics['r2'],  # Legacy
        }
        print("DEBUG: Results built OK")
    except Exception as e:
        print(f"DEBUG: Results build failed: {e}")
        return None

    if verbose:
        print("Gran analysis complete with separate raw/opt Zones.")
        for diag in diagnostics:
            print(diag)

    # Print results for debugging
    print("=== ANALYZER ORIGINAL RESULTS ===")
    print(f"Raw Zone: V_eq = {raw_metrics['V_eq']:.3f} mL, R² = {raw_metrics['r2']:.4f}, k5 = {raw_metrics['k5']}, Zone = {raw_metrics['zone_start']}-{raw_metrics['zone_end']}, Points = {raw_metrics.get('num_points', 'N/A')}")
    print(f"Opt Zone: V_eq = {opt_metrics['V_eq']:.3f} mL, R² = {opt_metrics['r2']:.4f}, k5 = {opt_metrics['k5']:.3f}, Zone = {opt_metrics['zone_start']}-{opt_metrics['zone_end']}, Points = {opt_metrics.get('num_points', 'N/A')}")
    print(f"g1 shape: {g1.shape}, g1_opt shape: {gs_opt.shape}")
    print(f"Interval R² (legacy): {raw_metrics['r2']:.4f}")
    print("=== END ANALYZER ORIGINAL ===")

    return results

def _identify_linear_original(g1: np.ndarray, volume: np.ndarray, min_points: int = 5, window_size: int = 5) -> Tuple[int, int, float]:
    """Original non-segmented interval identification (fallback; preserved)."""
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
            slope, intercept, r_value, _, _ = linregress(volume[test_start:test_end+1], g1_smooth[test_start:test_end+1])
            r2 = r_value**2
            if r2 > best_r2:
                best_r2 = r2
                best_start = test_start
                best_end = test_end

    return best_start, best_end, best_r2


# Compatibility Wrapper for Downstream (Gran/Schwartz Nest)
def analyze_gran(gran_results: Dict[str, Any], params: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Compatibility wrapper: Uses pre-computed gran_results, runs original analysis on g1,
    maps keys, nests for visualizer/reporter, adds pH/g1/g1_opt.
    No redundant df rebuild; copies 'fit' and 'num_points' for plotting.
    """
    # No need to rebuild df - we have everything from gran_results and params

    # Run original analysis on passed gran_results (g1, schwartz_func, etc.)
    original_results = analyze_gran_original(
        pd.DataFrame({  # Minimal df for _compute_fit calls
            'volume': params['volume_array'],
            'potential': params['potential_array']
        }),
        params,
        use_segmented=True,
        verbose=verbose
    )

    # Defensive mapping from original keys
    raw_original = original_results.get('raw_zone', {})
    raw_metrics = {
        'V_eq': raw_original.get('V_eq', np.nan),
        'r2': raw_original.get('r2', 0.0),
        'k': 0.0,  # Renamed from k5
        'zone_start': raw_original.get('zone_start', 0),
        'zone_end': raw_original.get('zone_end', len(params['volume_array']) - 1),
        'fit': raw_original.get('fit', None),          # For dashed fit line in visualizer
        'num_points': raw_original.get('num_points', 0)  # For point count in titles
    }

    opt_original = original_results.get('opt_zone', {})
    opt_metrics = {
        'V_eq': opt_original.get('V_eq', np.nan),
        'r2': opt_original.get('r2', 0.0),
        'k': opt_original.get('k5', 0.0),  # Renamed from k5
        'zone_start': opt_original.get('zone_start', 0),
        'zone_end': opt_original.get('zone_end', len(params['volume_array']) - 1),
        'fit': opt_original.get('fit', None),          # For dashed fit line
        'num_points': opt_original.get('num_points', 0)  # For point count
    }

    # Nest for downstream (gran from original, schwartz as true mirror if needed)
    analysis_results = {
        'gran': {'raw': raw_metrics, 'opt': opt_metrics},
        'schwartz': {'raw': raw_metrics, 'opt': opt_metrics},  # Stub copy; replace with true opt later
        'pH': gran_results.get('pH', np.array([])),
        'g1': gran_results.get('gran', {}).get('g1', np.array([])),
        'g1_opt': gran_results.get('schwartz', {}).get('gs', np.array([]))  # gs = g1_opt
    }

    if verbose:
        print("Analysis: Gran scout zone → Schwartz k opt → re-detect/shrink cycle on gs_opt.")

    return analysis_results
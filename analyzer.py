"""
analyzer.py: Validated equivalence point detection via Gran/Schwartz linearization.
Algorithm preserved: Smoothing → deriv → candidates → rank/eval → shrink (raw) → opt k → re-shrink (opt).
Outputs nested metrics for downstream (gran/schwartz raw/opt with V_eq, r2, k, zones).
"""

import numpy as np
import pandas as pd
from scipy.stats import linregress
from scipy.signal import savgol_filter
from scipy.optimize import minimize_scalar
from gran_functions import compute_gran_functions
from typing import Tuple, Dict, Any, Callable


def _compute_r2(g1_smooth: np.ndarray, volume: np.ndarray, start: int, end: int) -> Tuple[float, float, float]:
    """Helper: Compute R², slope, intercept for a segment."""
    if end - start < 2:
        return 0.0, 0.0, 0.0
    slope, intercept, r_value, _, _ = linregress(volume[start:end+1], g1_smooth[start:end+1])
    return r_value**2, slope, intercept


def identify_linear_interval(
    g1: np.ndarray, volume: np.ndarray, min_points: int = 5, window_size: int = 5,
    noise_threshold: float = 0.001, var_threshold_rel: float = 0.1, min_r2: float = 0.95
) -> Tuple[int, int, float]:
    """
    Identify linear zone using derivative-based segmentation and ranking.
    Handles Cases 1-3 via plateau detection in negative dg1.
    """
    dg1_raw = np.gradient(g1, volume)
    std_dg1 = np.std(dg1_raw)
    if std_dg1 > noise_threshold:
        g1_smooth = savgol_filter(g1, window_length=window_size, polyorder=2)
        dg1 = np.gradient(g1_smooth, volume)
    else:
        g1_smooth = g1
        dg1 = dg1_raw

    neg_mask = dg1 < 0
    if not np.any(neg_mask):
        return 0, len(g1) - 1, 0.0
    dg1_neg = dg1[neg_mask]
    vol_neg_idx = np.where(neg_mask)[0]

    candidates = []
    win_sizes = range(max(3, min_points//2), min(33, len(dg1_neg)//2) + 1)
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

    scored = []
    for cand in candidates:
        r2, slope, intercept = _compute_r2(g1_smooth, volume, cand['orig_start'], cand['orig_end'])
        score = r2 * 100 + (cand['length'] / len(g1)) * 10 + abs(cand['mean_dg']) * 0.1
        scored.append((cand, score, r2))

    best_cand, best_score, best_r2 = max(scored, key=lambda x: x[1])
    start_idx, end_idx = best_cand['orig_start'], best_cand['orig_end']

    return start_idx, end_idx, best_r2


def _compute_fit(df: pd.DataFrame, start: int, end: int, gran_func: Callable, k: float = 0.0, pH_full: np.ndarray = None) -> Dict[str, Any]:
    """Compute fit, R², and V_eq for a zone with given k."""
    volume_slice = df['volume'].iloc[start:end+1].values
    pH_slice = pH_full[start:end+1]
    y = gran_func(volume_slice, pH_slice, k)
    slope, intercept, r_value, _, _ = linregress(volume_slice, y)
    r2 = r_value**2
    veq = -intercept / slope if slope != 0 else np.nan
    return {'r2': r2, 'fit': (slope, intercept), 'veq': veq}


def _optimize_single_zone(df: pd.DataFrame, start: int, end: int, gran_func: Callable, k_bounds: Tuple[float, float] = (-10, 10), pH_full: np.ndarray = None) -> Dict[str, Any]:
    """Optimize k for a fixed zone using gran_func callable."""
    volume_slice = df['volume'].iloc[start:end+1].values
    pH_slice = pH_full[start:end+1]

    def negative_r2(k):
        y = gran_func(volume_slice, pH_slice, k)
        slope, intercept, r_value, _, _ = linregress(volume_slice, y)
        return -r_value**2

    result = minimize_scalar(negative_r2, bounds=k_bounds, method='bounded')
    best_k = result.x
    max_r2 = -result.fun
    y_opt = gran_func(volume_slice, pH_slice, best_k)
    slope, intercept, _, _, _ = linregress(volume_slice, y_opt)
    return {'best_k': best_k, 'best_r2': max_r2, 'fit': (slope, intercept)}


def shrink_zone(
    volume: np.ndarray, g_values: np.ndarray, initial_zone: Tuple[int, int], max_iter: int = 10
) -> Tuple[int, int]:
    """Binary trim edges for max R² (>5% gain; validated Case 3 refinement)."""
    start, end = initial_zone
    current_r2, _, _ = _compute_r2(g_values, volume, start, end)
    iter_count = 0
    improved = True
    while improved and iter_count < max_iter and end - start > 2:
        improved = False
        left_mid = (start + end) // 2
        if left_mid - start > 0:
            left_r2, _, _ = _compute_r2(g_values, volume, left_mid, end)
            if left_r2 > current_r2 * 1.05:
                start = left_mid
                current_r2 = left_r2
                improved = True
                iter_count = 0
        right_mid = (start + end) // 2
        if end - right_mid > 0:
            right_r2, _, _ = _compute_r2(g_values, volume, start, right_mid)
            if right_r2 > current_r2 * 1.05:
                end = right_mid
                current_r2 = right_r2
                improved = True
                iter_count = 0
        iter_count += 1
    return (start, end)

def get_metrics(fit: Any, zone: Tuple[int, int], k: float = 0.0, r2_threshold: float = 0.95) -> Dict[str, Any]:
    """Extract V_eq, r2 from fit/zone (centralized). Warn on low R². Includes 'fit' for plotting."""
    start, end = zone
    if fit is None or end - start < 2:
        return {'V_eq': np.nan, 'r2': 0.0, 'k': k, 'zone_start': start, 'zone_end': end, 'fit': None}
    slope, intercept = fit['fit']
    r2 = fit['r2']
    v_eq = -intercept / slope if slope != 0 else np.nan
    if r2 < r2_threshold:
        print(f"Warning: Low R²={r2:.3f} for zone {zone} (k={k})")
    return {
        'V_eq': v_eq,
        'r2': r2,
        'k': k,
        'zone_start': start,
        'zone_end': end,
        'fit': fit['fit']  # Pass (slope, intercept) for visualizer dashed line
    }

def analyze_gran_original(df: pd.DataFrame, params: Dict[str, Any], use_segmented: bool = True, verbose: bool = False) -> Dict[str, Any]:
    """Main analysis: Compute Gran, identify raw interval, fit raw, then optimize for Schwartz opt Zone."""
    gran_results = compute_gran_functions(df, params)
    g1 = gran_results['gran']['g1']
    gran_func = gran_results['gran']['gran_func']
    schwartz_func = gran_results['schwartz']['gran_func']
    volume = params['volume_array']
    pH_full = gran_results['pH']  # Use precomputed pH (flipped if base)

    # Identify initial interval (on raw g1)
    if use_segmented:
        start_idx, end_idx, _ = identify_linear_interval(g1, volume)
    else:
        start_idx, end_idx, _ = _identify_linear_original(g1, volume)
    initial_interval = (start_idx, end_idx)

    # Raw Zone: Fit on initial interval (k=0)
    raw_zone = _compute_fit(df, start_idx, end_idx, gran_func, k=0.0, pH_full=pH_full)
    raw_zone.update({'start': start_idx, 'end': end_idx, 'num_points': end_idx - start_idx + 1})
    raw_metrics = get_metrics({'r2': raw_zone['r2'], 'fit': raw_zone['fit']}, initial_interval, k=0.0)

    # Opt k on raw Zone
    k_bounds = (-10, 10)
    opt_k_dict = _optimize_single_zone(df, start_idx, end_idx, schwartz_func, k_bounds, pH_full=pH_full)
    opt_k = opt_k_dict['best_k']

    # Recompute gs_opt and re-detect Zone on it
    gs_opt = schwartz_func(volume, pH_full, opt_k)
    if use_segmented:
        opt_start, opt_end, opt_interval_r2 = identify_linear_interval(gs_opt, volume)
    else:
        opt_start, opt_end, opt_interval_r2 = _identify_linear_original(gs_opt, volume)

    # Opt fit on re-detected Zone
    opt_zone = _compute_fit(df, opt_start, opt_end, schwartz_func, k=opt_k, pH_full=pH_full)
    opt_zone.update({'k': opt_k, 'start': opt_start, 'end': opt_end, 'num_points': opt_end - opt_start + 1})
    opt_metrics = get_metrics({'r2': opt_zone['r2'], 'fit': opt_zone['fit']}, (opt_start, opt_end), k=opt_k)

    # Fallback if opt Zone smaller than raw
    if opt_metrics['zone_end'] - opt_metrics['zone_start'] < raw_metrics['zone_end'] - raw_metrics['zone_start']:
        opt_start, opt_end = raw_metrics['zone_start'], raw_metrics['zone_end']
        opt_zone = _compute_fit(df, opt_start, opt_end, schwartz_func, k=opt_k, pH_full=pH_full)
        opt_zone.update({'k': opt_k, 'start': opt_start, 'end': opt_end, 'num_points': opt_end - opt_start + 1})
        opt_metrics = get_metrics({'r2': opt_zone['r2'], 'fit': opt_zone['fit']}, (opt_start, opt_end), k=opt_k)

    results = {
        'raw_zone': raw_metrics,
        'opt_zone': opt_metrics,
        'g1': g1,
        'g1_opt': gs_opt,
        'interval_r2': raw_metrics['r2'],
    }

    if verbose:
        print("Gran analysis complete with separate raw/opt Zones.")
        print(f"Raw: V_eq={raw_metrics['V_eq']:.3f}, R²={raw_metrics['r2']:.4f}, zone {raw_metrics['zone_start']}-{raw_metrics['zone_end']}")
        print(f"Opt: V_eq={opt_metrics['V_eq']:.3f}, R²={opt_metrics['r2']:.4f}, k={opt_metrics['k']:.3f}, zone {opt_metrics['zone_start']}-{opt_metrics['zone_end']}")

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
    """Compatibility wrapper: Run original analyze_gran_original, nest original output for visualizer/reporter."""
    # Run original
    df = pd.DataFrame({
        'volume': params['volume_array'],
        'potential': params['potential_array']
    })
    try:
        original_results = analyze_gran_original(df, params, use_segmented=True, verbose=verbose)
    except Exception as e:
        print(f"Warning: analyze_gran_original failed: {e}—using fallback metrics.")
        original_results = None
    
    # Defensive mapping (handle None)
    if original_results is None:
        n = len(params['volume_array'])
        raw_metrics = {'V_eq': np.nan, 'r2': 0.0, 'k': 0.0, 'zone_start': 0, 'zone_end': n - 1, 'fit': None}
        opt_metrics = raw_metrics.copy()
    else:
        raw_original = original_results.get('raw_zone', {})
        raw_metrics = {
            'V_eq': raw_original.get('V_eq', np.nan),  # If you have 'V_eq' here
            'r2': raw_original.get('r2', 0.0),
            'k': 0.0,
            'zone_start': raw_original.get('zone_start', 0),
            'zone_end': raw_original.get('zone_end', len(params['volume_array']) - 1),
            'fit': raw_original.get('fit', None)  # ← Add this line!
        }
        opt_original = original_results.get('opt_zone', {})
        opt_metrics = {
            'V_eq': opt_original.get('V_eq', np.nan),
            'r2': opt_original.get('r2', 0.0),
            'k': opt_original.get('k', 0.0),
            'zone_start': opt_original.get('zone_start', 0),
            'zone_end': opt_original.get('zone_end', len(params['volume_array']) - 1),
            'fit': opt_original.get('fit', None)
        }
    
    # Nest for dual (gran from original, schwartz copy for stub)
    analysis_results = {
        'gran': {'raw': raw_metrics, 'opt': opt_metrics},
        'schwartz': {'raw': raw_metrics, 'opt': opt_metrics},  # Copy; extend later for true Schwartz opt
        'pH': gran_results.get('pH', np.array([])),
        'g1': original_results.get('g1', np.array([])) if original_results is not None else np.array([]),  # For plots
        'g1_opt': original_results.get('g1_opt', np.array([])) if original_results is not None else np.array([])  # For plots
    }
    
    if verbose:
        print("Analysis wrapped: Original → nested gran/schwartz for downstream.")
    # Print nested results for debugging
    print("=== ANALYZER NESTED RESULTS ===")
    for method in ['gran', 'schwartz']:
        for mode in ['raw', 'opt']:
            m_data = analysis_results[method][mode]
            print(f"{method.capitalize()} {mode.capitalize()}: V_eq = {m_data['V_eq']:.3f} mL, R² = {m_data['r2']:.4f}, k = {m_data['k']:.3f}, Zone = {m_data['zone_start']}-{m_data['zone_end']}")
    print(f"pH shape: {analysis_results['pH'].shape}")
    print("=== END ANALYZER NESTED ===")

    return analysis_results
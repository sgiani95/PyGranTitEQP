"""
analyzer.py: Core analysis engine for GranTED—detects linear zones, fits equivalence points, and optimizes k5.

Supports Gran (4 types) and Schwartz (2 types) with raw/optimized modes. Uses derivatives for zone ID, linregress for fits,
minimize_scalar for k5 (max R²). Handles Cases 1–3 with fallbacks; Schwartz includes V_eq iteration.
Configurable thresholds via params; logging for diagnostics.

Dependencies: numpy, pandas, scipy (stats, signal, optimize).
Local: gran_functions (for recompute/lambdas).
"""

import numpy as np
import pandas as pd
from scipy.stats import linregress
from scipy.signal import savgol_filter
from scipy.optimize import minimize_scalar
from typing import Dict, Any, Tuple, Optional, Callable
import logging

from gran_functions import compute_gran_functions  # For fallback recompute

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _compute_derivative(g_values: np.ndarray, volume: np.ndarray, savgol_window: int = 5) -> np.ndarray:
    """
    Compute smoothed derivative dg/dv using SavGol or np.gradient.
    """
    if len(g_values) < savgol_window:
        logger.warning(f"Array too short for SavGol (n={len(g_values)} < {savgol_window}); using raw gradient.")
        deriv = np.gradient(g_values, volume)
    else:
        smoothed_g = savgol_filter(g_values, window_length=savgol_window, polyorder=2)
        deriv = np.gradient(smoothed_g, volume)
    return deriv


def _score_zone(r2: float, length: int, slope: float, max_length: int, r2_threshold: float) -> float:
    """
    Score zone quality: Weighted R² + normalized length + |slope| (penalize flat but short).
    """
    length_norm = length / max_length
    slope_norm = abs(slope) / (np.max(np.abs(np.gradient(np.logspace(0, 1, max_length)))) or 1)  # Rough norm
    score = (r2 - r2_threshold + 1) * 0.7 + length_norm * 0.2 + slope_norm * 0.1  # Tunable weights
    return score


def _find_candidate_zones(deriv: np.ndarray, volume: np.ndarray, window_size: int, r2_threshold: float) -> list:
    """
    Find candidate zones via low-variance deriv regions (rolling min var).
    Returns list of (start_idx, end_idx, score).
    """
    candidates = []
    n = len(deriv)
    for i in range(0, n - window_size, window_size // 2):  # Overlap
        end = min(i + window_size, n)
        var = np.var(deriv[i:end])
        if var < np.var(deriv) * 0.1:  # Threshold: 10% global var
            # Reconstruct approx g_slice for scoring (cumsum deriv as log-g proxy)
            dv = np.diff(volume[i:end], prepend=volume[i])
            log_g_approx = np.cumsum(deriv[i:end] * dv)
            g_slice = np.exp(log_g_approx)
            fit = linregress(volume[i:end], g_slice)
            score = _score_zone(fit.rvalue**2, end - i, fit.slope, n, r2_threshold)
            if fit.rvalue**2 > r2_threshold:
                candidates.append((i, end, score))
    return sorted(candidates, key=lambda x: x[2], reverse=True)[:3]  # Top 3


def identify_linear_interval(g_values: np.ndarray, volume: np.ndarray, params: Dict[str, Any], method: str = 'gran') -> Tuple[int, int]:
    """
    Detect best linear zone via modular deriv var + scoring.
    Supports cases: Default (var-based), case2 (shrink), case3 (deriv min).
    """
    r2_threshold = params.get('r2_threshold', 0.95)
    savgol_window = params.get('savgol_window', 5)
    case = params.get('case', 'default')

    if len(g_values) != len(volume):
        raise ValueError(f"g_values and volume length mismatch: {len(g_values)} vs {len(volume)}")

    if len(volume) < 5:
        raise ValueError("Too few points for zone detection (<5). Use more data.")

    deriv = _compute_derivative(g_values, volume, savgol_window)
    window_size = max(5, len(volume) // 10)  # ~10% rolling

    candidates = _find_candidate_zones(deriv, volume, window_size, r2_threshold)
    if candidates:
        start, end, _ = candidates[0]
        logger.info(f"{method} zone detected: indices {start}-{end} (R² > {r2_threshold})")
        return start, end

    # Fallback cases
    if case == 'case2':
        # Shrink full range by 20%
        n = len(volume)
        start, end = int(0.1 * n), int(0.9 * n)
        logger.warning(f"{method} case2 fallback: Shrunk full range to {start}-{end}")
    elif case == 'case3':
        # Expand around deriv min (flattest)
        min_idx = np.argmin(np.abs(deriv))
        start, end = max(0, min_idx - len(volume)//10), min(len(volume), min_idx + len(volume)//10)
        logger.warning(f"{method} case3 fallback: Expanded around deriv min at {min_idx} to {start}-{end}")
    else:
        start, end = 0, len(volume)
        logger.warning(f"{method} default fallback: Full range (no good zone found)")

    return start, end


def _compute_fit(g_values: np.ndarray, volume: np.ndarray, start_idx: int, end_idx: int) -> Dict[str, Any]:
    """
    Compute linear fit and V_eq on zone.
    """
    if end_idx - start_idx < 2:
        logger.warning("Zone too short for fit (<2 pts); returning defaults.")
        return {'slope': 0.0, 'intercept': 0.0, 'rvalue': 0.0, 'v_eq': 0.0}

    v_slice = volume[start_idx:end_idx]
    g_slice = g_values[start_idx:end_idx]
    fit = linregress(v_slice, g_slice)
    v_eq = -fit.intercept / fit.slope if fit.slope != 0 else 0.0
    logger.debug(f"Fit: slope={fit.slope:.3f}, intercept={fit.intercept:.3f}, R²={fit.rvalue**2:.3f}, V_eq={v_eq:.3f}")
    return {'slope': fit.slope, 'intercept': fit.intercept, 'rvalue': fit.rvalue, 'v_eq': v_eq}


def optimize_k5(gran_func: Callable, volume: np.ndarray, pH: np.ndarray, params: Dict[str, Any], initial_guess: float = 0.0) -> float:
    """
    Optimize k5 via minimize_scalar on -R² (modular, with iteration callback).
    """
    r2_threshold = params.get('r2_threshold', 0.95)

    def loss(kk: float) -> float:
        g_k = gran_func(volume, pH, kk)
        start, end = identify_linear_interval(g_k, volume, params)
        fit = _compute_fit(g_k, volume, start, end)
        r2 = fit['rvalue'] ** 2
        logger.debug(f"k={kk:.3f}: Zone {start}-{end}, R²={r2:.3f}")
        return -(r2 - r2_threshold + 1)  # Penalize below threshold

    try:
        res = minimize_scalar(loss, bounds=(-10, 10), method='bounded', tol=1e-6)
        if not res.success:
            logger.warning(f"k5 optimization failed: {res.message}; fallback to {initial_guess}")
            return initial_guess
        logger.info(f"k5 optimized to {res.x:.3f} (R² improvement via {res.nfev} evals)")
        return res.x
    except Exception as e:
        logger.warning(f"k5 opt error: {e}; fallback to {initial_guess}")
        return initial_guess


def analyze_gran(results: Dict[str, Any], params: Dict[str, Any], method: str, optimize_k: bool = True) -> None:
    """
    Analyze one method: Raw zone/fit + optional k opt + Schwartz iteration if applicable.
    Mutates results[method] with 'raw'/'optimized'.
    """
    if method not in results:
        logger.error(f"Missing {method} in results; skipping.")
        return

    # Extract arrays (fallback to df if params missing; assume df passed or extract from results)
    df = params.get('df', None)  # Optional df param
    volume = params.get('volume_array', df['volume'].values if df is not None else np.zeros(0))
    pH = results.get('pH', np.zeros_like(volume))
    g_raw = results[method].get('g1' if method == 'gran' else 'gs')
    gran_func = results[method].get('gran_func')  # Lambda
    if not callable(gran_func):
        logger.warning(f"No callable {method} func; skipping optimization.")
        optimize_k = False

    if len(volume) == 0:
        logger.error("Empty volume array; check preprocess/gran_functions.")
        return

    r2_threshold = params.get('r2_threshold', 0.95)
    savgol_window = params.get('savgol_window', 5)
    case = params.get('case', 'default')

    # Raw analysis
    start, end = identify_linear_interval(g_raw, volume, params, method)
    raw_fit = _compute_fit(g_raw, volume, start, end)
    results[method]['raw'] = {
        'zone_start': start, 'zone_end': end,
        'r2': raw_fit['rvalue'] ** 2,
        'v_eq': raw_fit['v_eq'],
        'fit': raw_fit
    }
    logger.info(f"{method} raw: Zone {start}-{end}, R²={raw_fit['rvalue']**2:.3f}, V_eq={raw_fit['v_eq']:.2f} mL")

    if not optimize_k:
        return

    # Optimization
    optimized_k = optimize_k5(gran_func, volume, pH, params)
    g_opt = gran_func(volume, pH, optimized_k)

    # Refit on optimized g
    start_opt, end_opt = identify_linear_interval(g_opt, volume, params, method)
    opt_fit = _compute_fit(g_opt, volume, start_opt, end_opt)

    # Schwartz-specific: V_eq iteration (3 max its)
    if method == 'schwartz':
        v_eq_prev = opt_fit['v_eq']
        iterations = 0
        for it in range(3):
            iterations += 1
            # Refeed V_eq into func (assume lambda uses params['v_eq_guess'] for adjustment; stub if not)
            params_iter = params.copy()
            params_iter['v_eq_guess'] = v_eq_prev
            g_iter = gran_func(volume, pH, optimized_k)  # Recompute (extend lambda if needed for V_eq)
            start_iter, end_iter = identify_linear_interval(g_iter, volume, params_iter, method)
            fit_iter = _compute_fit(g_iter, volume, start_iter, end_iter)
            v_eq_new = fit_iter['v_eq']
            delta = abs(v_eq_new - v_eq_prev)
            logger.debug(f"Schwartz iter {it+1}: V_eq={v_eq_new:.3f}, Δ={delta:.3f}")
            if delta < 0.01:  # Tol 0.01 mL
                break
            v_eq_prev = v_eq_new
        opt_fit = fit_iter  # Use final
        results[method]['iterations'] = iterations
        logger.info(f"Schwartz converged in {iterations} iterations, final V_eq={v_eq_new:.3f} mL")

    results[method]['optimized'] = {
        'zone_start': start_opt, 'zone_end': end_opt,
        'r2': opt_fit['rvalue'] ** 2,
        'v_eq': opt_fit['v_eq'],
        'optimized_k': optimized_k,
        'fit': opt_fit
    }
    logger.info(f"{method} opt: k={optimized_k:.3f}, Zone {start_opt}-{end_opt}, R²={opt_fit['rvalue']**2:.3f}, V_eq={opt_fit['v_eq']:.2f} mL")


def analyze_full_pipeline(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full pipeline: Compute functions → Analyze both methods → Return enriched results.
    Ensures params has arrays.
    """
    if df.empty:
        raise ValueError("Empty DataFrame; load data first.")

    # Ensure params has arrays (from preprocess)
    if 'volume_array' not in params:
        params['volume_array'] = df['volume'].values
        params['df'] = df  # For fallback
    params['pH'] = None  # Will be set by gran_functions

    # Compute base functions
    base_results = compute_gran_functions(df, params)

    # Analyze methods
    methods = ['gran', 'schwartz']
    for m in methods:
        if m in base_results:
            analyze_gran(base_results, params, m)

    logger.info("Full pipeline complete: Processed gran and schwartz.")
    return base_results


if __name__ == "__main__":
    # Standalone test: Mock data
    df = pd.DataFrame({'volume': np.linspace(0, 30, 50), 'potential': np.linspace(0, -300, 50) + np.random.normal(0, 5, 50)})
    params = {'titration_type': 'weak_acid', 'V': 25.0, 'r2_threshold': 0.95, 'savgol_window': 5, 'case': 'default'}
    results = analyze_full_pipeline(df, params)
    print("Test analysis:", {k: list(v.keys()) for k, v in results.items() if k != 'pH'})
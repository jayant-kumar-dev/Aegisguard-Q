"""Depolarizing-channel adjustments to exact spectral leakage metrics."""

import math
from typing import Callable, List

from .information import shannon_entropy, spectral_distribution


def noisy_spectral_distribution(
    n: int, g: Callable[[int], int], p_depol: float = 0.0
) -> List[float]:
    if not 0.0 <= p_depol <= 1.0:
        raise ValueError("p_depol must be between 0 and 1")
    p = spectral_distribution(n, g)
    return [(1.0 - p_depol) * v + p_depol / (1 << n) for v in p]


def noisy_channel_metrics(
    n: int,
    g: Callable[[int], int],
    p_depol: float = 0.0,
    epsilon: float = 0.05,
) -> dict:
    p = noisy_spectral_distribution(n, g, p_depol)
    h = shannon_entropy(p)
    base = spectral_distribution(n, g)
    gamma = max(base) - sorted(base, reverse=True)[1] if len(base) > 1 else 0.0
    gamma_eff = (1.0 - p_depol) * gamma
    n_bound = (
        math.ceil((2.0 / gamma_eff ** 2) *
                  (n * math.log(2) + math.log(1.0 / epsilon)))
        if gamma_eff > 1e-12 else None
    )
    return {
        "p_depol": p_depol,
        "H_noisy": h,
        "MI_noisy": max(0.0, n - h),
        "gamma_eff": gamma_eff,
        "N_bound": n_bound,
    }

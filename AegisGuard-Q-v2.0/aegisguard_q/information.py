"""
Information-theoretic and identifiability metrics (AegisGuard-Q v2).

Implements the quantities introduced in the accompanying manuscript:

  * spectral_distribution : P_g(u) = W_g(u)^2 / 4^n
  * shannon_entropy       : H(P_g)
  * mutual_information    : I(X;W) = n - H(P_g)          (Theorem 2)
  * translation_stabilizer: Stab(P_g)                    (Definition 5)
  * spectral_ambiguity_index (SAI)                       (Definition 6)
  * probability_gap       : gamma = p_1 - p_2
  * empirical_mode_bound  : N >= (2/gamma^2)(n ln2 + ln(1/eps))  (Theorem 8)

All quantities are computed exactly from the Walsh spectrum; no sampling.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional

from .core import walsh_spectrum, _validate_n


def spectral_distribution(n: int, g: Callable[[int], int]) -> List[float]:
    """P_g(u) = W_g(u)^2 / 4^n. Sums to 1 by Parseval."""
    _validate_n(n)
    dim = 1 << n
    W = walsh_spectrum(n, g)
    return [(v * v) / (dim * dim) for v in W]


def shannon_entropy(p: List[float]) -> float:
    """H(P) = -sum_u P(u) log2 P(u), with 0 log 0 := 0."""
    h = 0.0
    for v in p:
        if v > 1e-15:
            h -= v * math.log2(v)
    return h


def mutual_information(n: int, g: Callable[[int], int]) -> float:
    """
    Theorem 2: for X uniform on F_2^n and W = X xor U with U ~ P_g,
        I(X;W) = n - H(P_g).
    Returned in bits.
    """
    return n - shannon_entropy(spectral_distribution(n, g))


def translation_stabilizer(n: int, g: Callable[[int], int],
                           tol: float = 1e-9) -> List[int]:
    """
    Definition 5: Stab(P_g) = { t : P_g(u) = P_g(u xor t) for all u }.

    Returned as a sorted list of the t values. By Theorem 7 the secret is
    exactly identifiable from unlimited independent queries iff this is {0}.

    Exact computation is O(4^n); intended for benchmark-scale n.
    """
    _validate_n(n)
    p = spectral_distribution(n, g)
    dim = 1 << n
    stab = []
    for t in range(dim):
        if all(abs(p[u] - p[u ^ t]) <= tol for u in range(dim)):
            stab.append(t)
    return stab


def spectral_ambiguity_index(n: int, g: Callable[[int], int],
                             tol: float = 1e-6) -> int:
    """Definition 6: number of indices attaining max_u |W_g(u)|."""
    W = [abs(v) for v in walsh_spectrum(n, g)]
    m = max(W)
    return sum(1 for v in W if v >= m - tol)


def probability_gap(n: int, g: Callable[[int], int]) -> float:
    """
    gamma = p_1 - p_2, the raw mode gap of P_g.
    Returns 0.0 when the maximum is not unique (Theorem 8 does not apply).
    """
    p = sorted(spectral_distribution(n, g), reverse=True)
    if len(p) < 2:
        return 0.0
    gap = p[0] - p[1]
    return gap if gap > 1e-12 else 0.0


def empirical_mode_bound(n: int, gamma: float,
                         epsilon: float = 0.05) -> Optional[int]:
    """
    Theorem 8: N >= (2/gamma^2) (n ln 2 + ln(1/epsilon)).
    Returns None when gamma == 0 (no unique mode).
    """
    if gamma <= 0:
        return None
    return math.ceil((2.0 / (gamma * gamma)) *
                     (n * math.log(2) + math.log(1.0 / epsilon)))


def max_normalized_walsh(n: int, g: Callable[[int], int]) -> float:
    """lambda = max_u |W_g(u)| / 2^n, the quantity bounded in Theorem 9."""
    return max(abs(v) for v in walsh_spectrum(n, g)) / (1 << n)

"""
aegisguard_q.core
=================

Quantum-leakage static analysis for deterministic-noise HB-style
authentication protocols. This module is the reference implementation of the
theory in "Spectral Characterization of Superposition Leakage in
Deterministic-LPN Authentication Protocols".

It is an INDEPENDENT reimplementation: it recomputes the fast Walsh-Hadamard
transform and all spectral metrics from first principles (it does not import
the earlier hb_superposition_sim_*.py research scripts), so agreement between
the two constitutes cross-validation.

Given a public Boolean noise function g: {0,1}^n -> {0,1}, it computes:

  - the Walsh spectrum W_g,
  - SAI(g)             (Spectral Ambiguity Index; Def. 1)
  - residual_ambiguity (log2 SAI; Def. 2)
  - delta_prob         (probability gap; Def. 3)
  - single_query_recovery_probability  (= Wg(0)^2 / 4^n, the tau=0 case)
  - leakage_entropy    (Def. 4, computed on the induced BV distribution)
  - tau                (classical noise density wt(g)/2^n)
  - completeness_bound (|0.5 - tau| upper bound, Theorem 3)
  - nonlinearity       (standard cryptographic Nl(g))
  - a LeakageClass verdict (AFFINE / PARTIAL / BENT / GENERIC)

and, for SAI(g)=1 targets, the Theorem-2 query complexity to recover the key.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Callable, List, Optional


# ----------------------------------------------------------------------
# Boolean / Walsh primitives (reimplemented from scratch)
# ----------------------------------------------------------------------

def _validate_n(n: int) -> None:
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    if n > 24:
        raise ValueError(
            f"n={n} exceeds the exact-analysis limit of 24 "
            "(2^24 floats ~ 128 MB). Use sampling-based analysis for larger n."
        )


def truth_table_signs(n: int, g: Callable[[int], int]) -> List[float]:
    """(-1)^{g(a)} for a = 0 .. 2^n - 1."""
    _validate_n(n)
    dim = 1 << n
    out = [0.0] * dim
    for a in range(dim):
        out[a] = -1.0 if (g(a) & 1) else 1.0
    return out


def fast_walsh_hadamard(vec: List[float]) -> List[float]:
    """
    In-place iterative fast Walsh-Hadamard transform (unnormalized).
    Returns the raw Walsh transform: values in [-2^n, 2^n].
    Length of vec must be a power of two.
    """
    a = list(vec)
    dim = len(a)
    if dim & (dim - 1) != 0:
        raise ValueError("input length must be a power of two")
    h = 1
    while h < dim:
        for i in range(0, dim, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j] = x + y
                a[j + h] = x - y
        h *= 2
    return a


def walsh_spectrum(n: int, g: Callable[[int], int]) -> List[float]:
    """Raw Walsh transform W_g(u) = sum_a (-1)^{g(a) XOR a.u}."""
    return fast_walsh_hadamard(truth_table_signs(n, g))


def hamming_weight(n: int, g: Callable[[int], int]) -> int:
    """Number of inputs where g(a) = 1."""
    _validate_n(n)
    return sum(1 for a in range(1 << n) if g(a) & 1)


# ----------------------------------------------------------------------
# Leakage report
# ----------------------------------------------------------------------

class LeakageClass(str, Enum):
    AFFINE = "AFFINE"      # SAI=1, gap=1: full key recovery in O(1) queries
    GENERIC = "GENERIC"    # SAI=1, 0<gap<1: recovery in Theorem-2 many queries
    PARTIAL = "PARTIAL"    # SAI>1 but < 2^n: recovery to an ambiguity coset
    BENT = "BENT"          # flat spectrum: no single-query leakage (sufficiency)


@dataclass
class LeakageReport:
    n: int
    sai: int
    residual_ambiguity: float
    delta_prob: float
    single_query_recovery_probability: float
    leakage_entropy: float
    tau: float
    completeness_bound: float
    nonlinearity: float
    leakage_class: LeakageClass
    query_complexity: Optional[int]  # Theorem 2, None if SAI>1
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["leakage_class"] = self.leakage_class.value
        return d


def _is_bent(n: int, abs_spectrum: List[float]) -> bool:
    """A function is bent iff n is even and |W_g(u)| = 2^(n/2) for all u."""
    if n % 2 != 0:
        return False
    target = 2.0 ** (n / 2)
    return all(abs(v - target) < 1e-9 for v in abs_spectrum)


def analyze_noise_function(
    n: int,
    g: Callable[[int], int],
    epsilon: float = 0.05,
) -> LeakageReport:
    """
    Full spectral leakage analysis of a deterministic noise function g.

    epsilon: target failure probability used for the Theorem-2 query-complexity
             estimate (only meaningful when SAI(g) == 1).
    """
    _validate_n(n)
    dim = 1 << n

    W = walsh_spectrum(n, g)
    absW = [abs(v) for v in W]
    max_abs = max(absW)

    # SAI = number of u achieving the maximum |W_g(u)| (within fp tolerance)
    sai = sum(1 for v in absW if v >= max_abs - 1e-6)
    residual = math.log2(sai)

    # probability gap Delta_prob = (|Wmax|^2 - |Wsecond|^2)/4^n  (Def. 3)
    sorted_abs = sorted(absW, reverse=True)
    w_max = sorted_abs[0]
    w_second = sorted_abs[1] if len(sorted_abs) > 1 else 0.0
    delta_prob = (w_max ** 2 - w_second ** 2) / (dim ** 2)

    # single-query exact-recovery probability = W_g(0)^2 / 4^n
    p_recover = (W[0] ** 2) / (dim ** 2)

    # leakage entropy of the induced BV distribution P(w) = W_g(w)^2 / 4^n
    #   (shift by x only permutes outcomes, so entropy is x-independent)
    entropy = 0.0
    for v in W:
        p = (v * v) / (dim ** 2)
        if p > 1e-15:
            entropy -= p * math.log2(p)

    # classical noise density and completeness bound (Theorem 3)
    wt = hamming_weight(n, g)
    tau = wt / dim
    completeness_bound = max_abs / (2 ** (n + 1))

    # standard cryptographic nonlinearity
    nl = (1 << (n - 1)) - 0.5 * max_abs

    # classify
    notes: List[str] = []
    if _is_bent(n, absW):
        leakage_class = LeakageClass.BENT
        query_complexity = None
        notes.append(
            "Flat Walsh spectrum: no outcome is resolvably heavier than any "
            "other. Single-query BV leaks zero bits (Corollary 1.2, sufficiency)."
        )
    elif sai == 1:
        # gap in raw probabilities for the Theorem-2 bound
        p1 = (w_max ** 2) / (dim ** 2)
        p2 = (w_second ** 2) / (dim ** 2)
        gamma = p1 - p2
        if gamma > 1e-12:
            query_complexity = math.ceil(
                (2.0 / gamma ** 2) * (n * math.log(2) + math.log(1.0 / epsilon))
            )
        else:
            query_complexity = None
        if abs(nl) < 1e-9:
            leakage_class = LeakageClass.AFFINE
            notes.append("Affine noise: secret recovered in O(1) queries.")
        else:
            leakage_class = LeakageClass.GENERIC
            notes.append(
                f"Unique spectral mode: secret recovered in ~{query_complexity} "
                f"queries at eps={epsilon} (Theorem 2)."
            )
    else:
        leakage_class = LeakageClass.PARTIAL
        query_complexity = None
        notes.append(
            f"SAI={sai}: repeated queries narrow the secret to a computable "
            f"{sai}-element coset, not a point."
        )

    return LeakageReport(
        n=n,
        sai=sai,
        residual_ambiguity=residual,
        delta_prob=delta_prob,
        single_query_recovery_probability=p_recover,
        leakage_entropy=entropy,
        tau=tau,
        completeness_bound=completeness_bound,
        nonlinearity=nl,
        leakage_class=leakage_class,
        query_complexity=query_complexity,
        notes=notes,
    )

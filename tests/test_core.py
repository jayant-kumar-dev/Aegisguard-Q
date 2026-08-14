"""
Regression tests for AegisGuard-Q.

These assert the closed-form identities proved in the paper, so that any future
change that silently breaks the math fails loudly. Two independent checks:

  (A) internal-consistency checks against the paper's theorems, and
  (B) cross-validation against the separate hb_superposition_sim_* research
      scripts (a genuinely independent implementation using numpy statevector
      simulation), confirming the two agree to floating-point precision.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aegisguard_q import analyze_noise_function, LeakageClass, walsh_spectrum
from aegisguard_q import noise_functions as nf


# ----------------------------------------------------------------------
# (A) Closed-form identity checks
# ----------------------------------------------------------------------

def test_affine_is_full_leak():
    """Affine noise => SAI=1, Nl=0, class AFFINE, recovery prob = 1."""
    for n in (4, 6, 8):
        r = analyze_noise_function(n, nf.affine(n))
        assert r.sai == 1
        assert abs(r.nonlinearity) < 1e-9
        assert r.leakage_class == LeakageClass.AFFINE
        assert abs(r.single_query_recovery_probability - 1.0) < 1e-9


def test_linear_deterministic_still_sai1():
    """g(a)=a.s is linear: SAI=1 and Nl=0 (it is affine), so class AFFINE."""
    n = 8
    r = analyze_noise_function(n, nf.linear(n, s=0b10110))
    assert r.sai == 1
    assert abs(r.nonlinearity) < 1e-9
    assert r.leakage_class == LeakageClass.AFFINE


def test_bent_is_flat_and_zero_leak():
    """
    Bent noise => flat spectrum |W|=2^(n/2), SAI=2^n, class BENT,
    delta_prob = 0, and Theorem 3 equality |0.5 - tau| = 2^(-n/2-1).
    """
    for n in (4, 6, 8, 10):
        g = nf.bent_inner_product(n)
        r = analyze_noise_function(n, g)
        assert r.sai == (1 << n)
        assert r.leakage_class == LeakageClass.BENT
        assert abs(r.delta_prob) < 1e-9
        # Theorem 3 corollary equality
        assert abs(abs(0.5 - r.tau) - 2.0 ** (-n / 2 - 1)) < 1e-9


def test_bent_nonlinearity_meets_bound():
    """Bent function achieves the maximal nonlinearity 2^(n-1) - 2^(n/2-1)."""
    for n in (4, 6, 8):
        g = nf.bent_inner_product(n)
        r = analyze_noise_function(n, g)
        max_nl = (1 << (n - 1)) - (1 << (n // 2 - 1))
        assert abs(r.nonlinearity - max_nl) < 1e-9


def test_walsh_parseval():
    """Parseval: sum_u W_g(u)^2 = 2^(2n) = 4^n for any Boolean g."""
    n = 8
    g = nf.random_anf(n, degree=3, num_terms=7, seed=1)
    W = walsh_spectrum(n, g)
    assert abs(sum(v * v for v in W) - (1 << (2 * n))) < 1e-6


def test_recovery_probability_equals_wg0_squared():
    """P(recover x) = W_g(0)^2 / 4^n exactly."""
    n = 8
    g = nf.random_anf(n, degree=2, num_terms=4, seed=2)
    W = walsh_spectrum(n, g)
    r = analyze_noise_function(n, g)
    expected = (W[0] ** 2) / ((1 << n) ** 2)
    assert abs(r.single_query_recovery_probability - expected) < 1e-12


def test_generic_has_query_complexity():
    """A unique-mode nonlinear g gets a finite Theorem-2 query estimate."""
    n = 8
    # pick a g that is not affine and (usually) has a unique spectral max
    for seed in range(20):
        g = nf.random_anf(n, degree=3, num_terms=9, seed=seed)
        r = analyze_noise_function(n, g)
        if r.leakage_class == LeakageClass.GENERIC:
            assert r.query_complexity is not None
            assert r.query_complexity > 0
            return
    pytest.skip("no GENERIC instance found in seed range (rare)")


def test_n_validation():
    with pytest.raises(ValueError):
        analyze_noise_function(0, nf.affine(1))
    with pytest.raises(ValueError):
        analyze_noise_function(25, nf.affine(25))


# ----------------------------------------------------------------------
# (B) Cross-validation against the independent research simulator
# ----------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_cross_validate_against_research_sim(seed):
    """
    The research script hb_superposition_sim computes the BV measurement
    distribution by numpy statevector simulation. Its max probability and
    entropy must match AegisGuard-Q's spectral computation.
    """
    numpy = pytest.importorskip("numpy")
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, os.path.abspath(root))
    try:
        from hb_superposition_sim import run_bv_attack
    except Exception:
        pytest.skip("research simulator not available in this environment")

    n = 8
    g = nf.random_anf(n, degree=3, num_terms=6, seed=seed)
    # research sim needs a secret x; entropy/maxprob are x-invariant
    probs = run_bv_attack(n, 0, g)
    sim_entropy = float(
        -sum(p * math.log2(p) for p in probs if p > 1e-15)
    )
    r = analyze_noise_function(n, g)
    assert abs(r.leakage_entropy - sim_entropy) < 1e-6
    assert abs(r.single_query_recovery_probability - float(probs[0])) < 1e-9

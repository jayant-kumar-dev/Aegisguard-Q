"""Regression tests for the v2 information-theoretic layer."""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aegisguard_q import noise_functions as nf
from aegisguard_q.information import (
    spectral_distribution, shannon_entropy, mutual_information,
    translation_stabilizer, spectral_ambiguity_index, probability_gap,
    empirical_mode_bound, max_normalized_walsh,
)
from aegisguard_q.core import hamming_weight

EVEN = [4, 6, 8]
ODD = [3, 5, 7]


def test_parseval():
    for n in EVEN + ODD:
        g = nf.random_anf(n, 3, 7, seed=1)
        assert abs(sum(spectral_distribution(n, g)) - 1.0) < 1e-9


def test_affine_full_leakage():
    for n in EVEN:
        g = nf.affine(n, s=1, c=0)
        assert abs(mutual_information(n, g) - n) < 1e-9
        assert translation_stabilizer(n, g) == [0]
        assert spectral_ambiguity_index(n, g) == 1


def test_bent_zero_leakage():
    for n in EVEN:
        g = nf.bent_inner_product(n)
        assert abs(mutual_information(n, g)) < 1e-9
        assert len(translation_stabilizer(n, g)) == (1 << n)
        assert abs(max_normalized_walsh(n, g) - 2 ** (-n / 2)) < 1e-12


def test_bent_completeness_equality():
    """Corollary to Theorem 9: |tau - 1/2| = 2^{-n/2-1} for bent g."""
    for n in EVEN:
        g = nf.bent_inner_product(n)
        tau = hamming_weight(n, g) / (1 << n)
        assert abs(abs(tau - 0.5) - 2 ** (-n / 2 - 1)) < 1e-12


def test_odd_semibent():
    """One bit of leakage, 2^{n-1} stabilizer, lambda = 2^{(1-n)/2}."""
    for n in ODD:
        g = nf.semibent_odd(n)
        assert abs(mutual_information(n, g) - 1.0) < 1e-9
        assert len(translation_stabilizer(n, g)) == (1 << (n - 1))
        assert abs(max_normalized_walsh(n, g) - 2 ** ((1 - n) / 2)) < 1e-12


def test_mi_identity_matches_entropy():
    """Theorem 2: I(X;W) = n - H(P_g) on arbitrary instances."""
    for n in EVEN + ODD:
        g = nf.random_anf(n, 2, 5, seed=n)
        h = shannon_entropy(spectral_distribution(n, g))
        assert abs(mutual_information(n, g) - (n - h)) < 1e-9


def test_theorem9_bound_holds():
    """|1 - 2 tau| <= lambda for every tested function."""
    for n in EVEN + ODD:
        for g in [nf.affine(n, 1, 0), nf.random_anf(n, 3, 6, seed=n)]:
            tau = hamming_weight(n, g) / (1 << n)
            assert abs(1 - 2 * tau) <= max_normalized_walsh(n, g) + 1e-9


def test_stabilizer_is_subgroup():
    """Stab is closed under XOR and contains 0."""
    for n in [3, 4, 5]:
        g = nf.random_anf(n, 2, 4, seed=7)
        S = set(translation_stabilizer(n, g))
        assert 0 in S
        for a in S:
            for b in S:
                assert (a ^ b) in S


def test_unique_mode_implies_trivial_stabilizer():
    for n in EVEN:
        g = nf.random_anf(n, 3, 9, seed=3)
        if spectral_ambiguity_index(n, g) == 1:
            assert translation_stabilizer(n, g) == [0]


def test_empirical_mode_bound_formula():
    n, gamma, eps = 6, 0.0390625, 0.05
    expected = math.ceil((2 / gamma ** 2) * (n * math.log(2) + math.log(1 / eps)))
    assert empirical_mode_bound(n, gamma, eps) == expected == 9378


def test_no_bound_without_unique_mode():
    g = nf.bent_inner_product(4)
    assert probability_gap(4, g) == 0.0
    assert empirical_mode_bound(4, 0.0) is None

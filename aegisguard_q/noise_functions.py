"""
aegisguard_q.noise_functions
============================

Constructors for the deterministic Boolean noise functions g: {0,1}^n -> {0,1}
studied in the paper. Each returns a callable g(a) -> {0,1}.
"""

from __future__ import annotations

import random
from itertools import combinations
from typing import Callable, List, Tuple


def _popcount_mod2(v: int) -> int:
    return bin(v).count("1") & 1


def affine(n: int, s: int = 0, c: int = 0) -> Callable[[int], int]:
    """g(a) = a.s XOR c  (affine; Nl = 0). Default s=c=0 gives the constant 0."""
    return lambda a: _popcount_mod2(a & s) ^ (c & 1)


def linear(n: int, s: int) -> Callable[[int], int]:
    """g(a) = a.s  (deterministic but linear; still SAI=1, recovers x XOR s)."""
    return lambda a: _popcount_mod2(a & s)


def random_anf(
    n: int, degree: int, num_terms: int, seed: int | None = None
) -> Callable[[int], int]:
    """
    g(a) = XOR of `num_terms` random monomials, each an AND of `degree`
    distinct input bits. Controls algebraic degree / nonlinearity.
    """
    rng = random.Random(seed)
    all_combos = list(combinations(range(n), min(degree, n)))
    monomials = rng.sample(all_combos, min(num_terms, len(all_combos)))

    def g(a: int) -> int:
        val = 0
        for idx in monomials:
            term = 1
            for i in idx:
                term &= (a >> i) & 1
            val ^= term
        return val

    return g


def keyed_ac0_mod2_prf(n: int, key_s: int, mask_t: int):
    return lambda a: _popcount_mod2(a & key_s) ^ int(
        all(((a ^ key_s) >> i) & 1 for i in range(n) if (mask_t >> i) & 1)
    )


def keyed_tribes_dlpn(n: int, key_s: int, width: int = 2):
    width = max(1, width)
    clauses = max(1, n // width)

    def g(a: int) -> int:
        shifted = a ^ key_s
        return int(any(
            all((shifted >> (clause * width + i)) & 1
                for i in range(width)
                if clause * width + i < n)
            for clause in range(clauses)
        ))

    return g


def keyed_mod2_mod3_prf(n: int, key_s: int):
    return lambda a: ((_popcount_mod2(a & key_s) +
                       (a & key_s).bit_count() % 3) & 1)


def bent_inner_product(n: int) -> Callable[[int], int]:
    """
    Maiorana-McFarland inner-product bent function (requires even n):
    g(a) = XOR_{i<n/2} a_i * a_{i+n/2}.  Provably bent for every even n.
    """
    if n % 2 != 0:
        raise ValueError("bent inner-product construction requires even n")
    half = n // 2

    def g(a: int) -> int:
        val = 0
        for i in range(half):
            bi = (a >> i) & 1
            bj = (a >> (half + i)) & 1
            val ^= (bi & bj)
        return val

    return g


def semibent_odd(n: int) -> Callable[[int], int]:
    """
    Odd-dimensional semibent benchmark (AegisGuard-Q v2).

    For odd n, no bent function exists. We extend a Maiorana-McFarland bent
    function on the first n-1 (even) variables, ignoring the final bit:

        g(a) = bent_{n-1}(a mod 2^{n-1}).

    The final variable is unused, so the Walsh spectrum satisfies
        W_g(v, 0) = 2 * W_bent(v),   W_g(v, 1) = 0,
    giving exactly 2^{n-1} nonzero coefficients of equal magnitude
    2^{(n+1)/2}. Hence H(P_g) = n-1, I(X;W) = 1 bit, and the translation
    stabilizer has 2^{n-1} elements.
    """
    if n % 2 == 0:
        raise ValueError("semibent_odd construction requires odd n")
    base = bent_inner_product(n - 1)
    mask = (1 << (n - 1)) - 1

    def g(a: int) -> int:
        return base(a & mask)

    return g

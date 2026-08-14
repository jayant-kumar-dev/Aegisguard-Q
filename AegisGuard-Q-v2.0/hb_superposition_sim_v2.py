"""
hb_superposition_sim_v2.py

Extends hb_superposition_sim.py with a formal cryptographic treatment:

THEOREM. For oracle h(a) = a.x XOR g(a), the BV-circuit measurement
distribution is exactly

    P(measure = w) = W_g(x XOR w)^2 / 4^n

where W_g(u) = sum_a (-1)^{g(a) XOR a.u} is the standard (unnormalized)
Walsh transform of g alone. Consequently:

  * P(exact recovery of x) = W_g(0)^2 / 4^n   (squared bias of g toward 0)
  * best-case attacker success = max_w P(w) = (2^n - 2*Nl(g))^2 / 4^n
    where Nl(g) is g's standard cryptographic nonlinearity.
  * For BENT g (flat Walsh spectrum, |W_g(u)| = 2^(n/2) for all u),
    P(w) = 1/2^n for every outcome -> provably zero information leakage,
    not just empirically small.

This file (1) verifies the theorem numerically against the direct
statevector simulation, (2) constructs an explicit bent function
(Maiorana-McFarland inner-product construction) and shows it achieves
exactly uniform output, and (3) redoes the nonlinearity sweep using the
correct formal metric Nl(g) instead of "number of AND terms".
"""

import numpy as np
import random

from hb_superposition_sim import (
    popcount_mod2,
    walsh_hadamard_transform,
    run_bv_attack,
    make_nonlinear_deterministic_noise,
)


# ----------------------------------------------------------------------
# Formal Walsh / nonlinearity machinery
# ----------------------------------------------------------------------

def truth_table(n: int, g) -> np.ndarray:
    """+-1 sign vector for Boolean function g: {0,1}^n -> {0,1}."""
    dim = 1 << n
    return np.array([(-1.0) ** g(a) for a in range(dim)])


def raw_walsh_transform(signs: np.ndarray) -> np.ndarray:
    """
    Standard (unnormalized) Walsh-Hadamard transform: W_g(u) = sum_a signs[a] * (-1)^{a.u}
    Values are integers in [-2^n, 2^n].
    """
    a = signs.copy().astype(np.float64)
    dim = len(a)
    h = 1
    while h < dim:
        for i in range(0, dim, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j], a[j + h] = x + y, x - y
        h *= 2
    return a


def nonlinearity(n: int, g) -> float:
    """Nl(g) = 2^(n-1) - (1/2) * max_u |W_g(u)|"""
    W = raw_walsh_transform(truth_table(n, g))
    return (1 << (n - 1)) - 0.5 * np.max(np.abs(W))


def bent_ip_function(n: int):
    """
    Maiorana-McFarland inner-product bent function (n even):
    g(a) = a_0 a_(n/2) XOR a_1 a_(n/2+1) XOR ... XOR a_(n/2-1) a_(n-1)
    Provably bent for every even n.
    """
    assert n % 2 == 0, "bent IP construction requires even n"
    half = n // 2

    def g(a: int) -> int:
        val = 0
        for i in range(half):
            bi = (a >> i) & 1
            bj = (a >> (half + i)) & 1
            val ^= (bi & bj)
        return val

    return g


def random_anf_function(n: int, degree: int, num_terms: int, seed=None):
    """
    Random Boolean function as XOR of `num_terms` random monomials of the
    given algebraic degree (e.g. degree=3 -> random triple-AND terms).
    Gives a formal-degree-controlled family, replacing the earlier
    ad hoc 'number of AND pairs' construction.
    """
    rng = random.Random(seed)

    def make_monomial():
        idx = rng.sample(range(n), degree)
        return tuple(idx)

    monomials = [make_monomial() for _ in range(num_terms)]

    def g(a: int) -> int:
        val = 0
        for idx in monomials:
            term = 1
            for i in idx:
                term &= (a >> i) & 1
            val ^= term
        return val

    return g


# ----------------------------------------------------------------------
# Experiment 4: verify the closed-form theorem directly
# ----------------------------------------------------------------------

def experiment_verify_theorem(n=8, trials=5):
    print("=== Experiment 4: Verify P(w) = W_g(x XOR w)^2 / 4^n ===")
    dim = 1 << n
    for _ in range(trials):
        x = random.randrange(dim)
        g = random_anf_function(n, degree=3, num_terms=6, seed=None)
        probs_sim = run_bv_attack(n, x, g)               # direct statevector simulation
        Wg = raw_walsh_transform(truth_table(n, g))       # formal Walsh transform of g
        probs_theory = np.array([Wg[x ^ w] ** 2 for w in range(dim)]) / (dim ** 2)
        max_err = np.max(np.abs(probs_sim - probs_theory))
        print(f"  x={x:0{n}b}: max |P_sim - P_theory| = {max_err:.2e}  "
              f"{'OK' if max_err < 1e-9 else 'MISMATCH'}")
    print()


# ----------------------------------------------------------------------
# Experiment 5: bent function -> provably uniform output
# ----------------------------------------------------------------------

def experiment_bent_function(n=10, trials=3):
    print("=== Experiment 5: Bent function noise -> provable zero leakage ===")
    dim = 1 << n
    g = bent_ip_function(n)
    Nl = nonlinearity(n, g)
    max_possible_Nl = (1 << (n - 1)) - (1 << (n // 2 - 1))
    print(f"  n={n}, Nl(g) = {Nl}  (max possible for even n = {max_possible_Nl}, "
          f"{'MATCHES bent bound' if Nl == max_possible_Nl else 'not bent!'})")

    for _ in range(trials):
        x = random.randrange(dim)
        probs = run_bv_attack(n, x, g)
        uniform_val = 1.0 / dim
        max_dev = np.max(np.abs(probs - uniform_val))
        print(f"  x={x:0{n}b}: max deviation from uniform (1/2^n={uniform_val:.6f}) "
              f"= {max_dev:.2e}  -> {'PROVABLY UNIFORM' if max_dev < 1e-9 else 'LEAKS INFO'}")
    print()


# ----------------------------------------------------------------------
# Experiment 6: corrected sweep, formal nonlinearity on the x-axis
# ----------------------------------------------------------------------

def experiment_formal_sweep(n=10, samples_per_degree=8):
    print("=== Experiment 6: Attack success vs formal nonlinearity Nl(g) ===")
    dim = 1 << n
    max_bent_nl = (1 << (n - 1)) - (1 << (n // 2 - 1))
    print(f"  n={n}. Theoretical bound: max_w P(w) = (1 - Nl(g)/2^(n-1))^2")
    print(f"  Bent-function nonlinearity bound for this n: {max_bent_nl}\n")
    print(f"  {'degree':>6} | {'terms':>5} | {'Nl(g)':>7} | {'Nl/2^(n-1)':>10} | "
          f"{'max P(w) sim':>13} | {'theory pred':>12}")
    print("  " + "-" * 68)

    configs = [(1, 1), (2, 2), (2, 6), (3, 6), (3, 12), (4, 12), (4, 20)]
    for degree, num_terms in configs:
        for _ in range(samples_per_degree // samples_per_degree):  # one rep, kept loop for clarity
            x = random.randrange(dim)
            g = random_anf_function(n, degree=degree, num_terms=num_terms, seed=None)
            Nl = nonlinearity(n, g)
            probs = run_bv_attack(n, x, g)
            max_p_sim = float(np.max(probs))
            theory_pred = (1 - Nl / (1 << (n - 1))) ** 2
            print(f"  {degree:>6} | {num_terms:>5} | {Nl:>7.0f} | "
                  f"{Nl/(1<<(n-1)):>10.4f} | {max_p_sim:>13.6f} | {theory_pred:>12.6f}")

    # bent function as the terminal / worst-case-for-attacker point
    g_bent = bent_ip_function(n)
    Nl_bent = nonlinearity(n, g_bent)
    x = random.randrange(dim)
    probs = run_bv_attack(n, x, g_bent)
    max_p_sim = float(np.max(probs))
    theory_pred = (1 - Nl_bent / (1 << (n - 1))) ** 2
    print(f"  {'bent':>6} | {'--':>5} | {Nl_bent:>7.0f} | "
          f"{Nl_bent/(1<<(n-1)):>10.4f} | {max_p_sim:>13.6f} | {theory_pred:>12.6f}")
    print(f"\n  (1/2^n baseline = {1.0/dim:.6f} -- bent function's max P(w) should match this)")
    print()


if __name__ == "__main__":
    random.seed(7)
    experiment_verify_theorem(n=8, trials=5)
    experiment_bent_function(n=10, trials=3)
    experiment_formal_sweep(n=10)

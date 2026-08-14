#!/usr/bin/env python3
"""
Experiment driver for the accompanying manuscript (AegisGuard-Q v2).

Regenerates Table 1 (exact spectral metrics across benchmark families) and
Table 2 (empirical mode-recovery failure rates) directly from the library.
All randomness is seeded and documented; running this script reproduces the
published tables exactly.

    python experiments.py
"""

from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from aegisguard_q import noise_functions as nf
from aegisguard_q.core import hamming_weight
from aegisguard_q.information import (
    spectral_distribution,
    shannon_entropy,
    mutual_information,
    translation_stabilizer,
    spectral_ambiguity_index,
    probability_gap,
    empirical_mode_bound,
    max_normalized_walsh,
)

# Documented seeds for the pseudorandom benchmark instances.
# Seed 6 is chosen so the n=6 instance has a unique spectral mode, which is
# the regime where Theorem 8 applies; the others are arbitrary fixed seeds.
RANDOM_SEEDS = {4: 10, 6: 2, 8: 10}

# Epsilon used for the Theorem 8 sample-complexity figure.
EPSILON = 0.05

# Trials used for the Table 2 Monte-Carlo study.
TRIALS = 3000
TABLE2_N_VALUES = [250, 500, 1000, 2000, 5000]


def random_truth_table(n: int, seed: int):
    """Uniformly random Boolean function on n bits, seeded and reproducible."""
    rng = random.Random(seed)
    tt = [rng.getrandbits(1) for _ in range(1 << n)]
    return lambda a: tt[a]


def benchmark_families():
    """Yields (family_label, n, g) for every row of Table 1."""
    for n in (4, 6, 8):
        yield "Affine", n, nf.affine(n, s=1, c=0)
        yield "Bent", n, nf.bent_inner_product(n)
        yield "Random", n, random_truth_table(n, RANDOM_SEEDS[n])
    for n in (3, 5, 7):
        yield "Odd-semibent", n, nf.semibent_odd(n)


def row_metrics(n, g):
    p = spectral_distribution(n, g)
    return {
        "tau": hamming_weight(n, g) / (1 << n),
        "lambda": max_normalized_walsh(n, g),
        "H": shannon_entropy(p),
        "MI": mutual_information(n, g),
        "S": len(translation_stabilizer(n, g)),
        "SAI": spectral_ambiguity_index(n, g),
        "gamma": probability_gap(n, g),
    }


def table1():
    print("Table 1: Exact spectral metrics (AegisGuard-Q v2)")
    hdr = f"{'Family':<14}{'n':>3}{'tau':>9}{'lambda':>9}{'H':>10}{'MI':>9}{'|S|':>6}{'SAI':>6}{'gamma':>10}"
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for label, n, g in benchmark_families():
        m = row_metrics(n, g)
        rows.append((label, n, m))
        print(f"{label:<14}{n:>3}{m['tau']:>9.4f}{m['lambda']:>9.4f}"
              f"{m['H']:>10.4f}{m['MI']:>9.4f}{m['S']:>6d}{m['SAI']:>6d}"
              f"{m['gamma']:>10.4f}")
    return rows


def check_identities(rows):
    """Assert the closed-form predictions of the manuscript on every row."""
    ok = True
    for label, n, m in rows:
        # Theorem 2: MI = n - H
        if abs(m["MI"] - (n - m["H"])) > 1e-9:
            print(f"  FAIL MI identity: {label} n={n}"); ok = False
        # Theorem 9: |1 - 2 tau| <= lambda
        if abs(1 - 2 * m["tau"]) > m["lambda"] + 1e-9:
            print(f"  FAIL Theorem 9 bound: {label} n={n}"); ok = False
        if label == "Bent":
            if abs(m["lambda"] - 2 ** (-n / 2)) > 1e-9: 
                print(f"  FAIL bent lambda: n={n}"); ok = False
            if abs(m["MI"]) > 1e-9:
                print(f"  FAIL bent MI: n={n}"); ok = False
            if m["S"] != (1 << n):
                print(f"  FAIL bent stabilizer: n={n}"); ok = False
        if label == "Affine":
            if abs(m["MI"] - n) > 1e-9:
                print(f"  FAIL affine MI: n={n}"); ok = False
            if m["S"] != 1:
                print(f"  FAIL affine stabilizer: n={n}"); ok = False
        if label == "Odd-semibent":
            if abs(m["MI"] - 1.0) > 1e-9:
                print(f"  FAIL semibent MI: n={n}"); ok = False
            if m["S"] != (1 << (n - 1)):
                print(f"  FAIL semibent stabilizer: n={n}"); ok = False
    print("\nClosed-form identity checks:", "ALL PASS" if ok else "FAILURES")
    return ok


def table2():
    """Monte-Carlo failure rate of empirical-mode recovery, unique-mode instance."""
    import numpy as np

    target = None
    for n in (6, 8, 4):
        g = random_truth_table(n, RANDOM_SEEDS[n])
        if spectral_ambiguity_index(n, g) == 1:
            target = (n, g)
            break
    if target is None:
        print("\nNo unique-mode pseudorandom benchmark; Table 2 skipped.")
        return None

    n, g = target
    p = np.array(spectral_distribution(n, g), dtype=float)
    p = p / p.sum()
    gamma = probability_gap(n, g)
    bound = empirical_mode_bound(n, gamma, EPSILON)
    mode = int(np.argmax(p))

    print(f"\nTable 2: Empirical mode failure, seeded random n={n} instance")
    print(f"  gamma = {gamma}, epsilon = {EPSILON}, Theorem 8 bound N >= {bound}")
    print(f"{'N':>8}{'Failure rate':>16}")
    print("-" * 24)

    rng = np.random.default_rng(20260814)
    results = []
    for N in TABLE2_N_VALUES + [bound]:
        counts = rng.multinomial(N, p, size=TRIALS)
        failures = int((counts.argmax(axis=1) != mode).sum())
        rate = failures / TRIALS
        results.append((N, rate))
        print(f"{N:>8}{rate:>16.4f}")
    return n, gamma, bound, results


if __name__ == "__main__":
    rows = table1()
    ok = check_identities(rows)
    table2()
    sys.exit(0 if ok else 1)

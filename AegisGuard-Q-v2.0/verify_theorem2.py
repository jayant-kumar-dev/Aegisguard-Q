"""
verify_theorem2.py -- empirical verification of Theorem 2's sample-complexity
bound N >= (2/gamma^2)(n ln2 + ln(1/eps)) for single-mode (SAI=1) BV
distributions from deterministic-LPN oracles.

Also demonstrates that the earlier "by analogy" bound (2/Delta^2)ln(4/eps)
FAILS, which is why the corrected union-bound version was needed.
"""
import numpy as np
from hb_superposition_sim import run_bv_attack
from hb_superposition_sim_v2 import random_anf_function


def full_fail(probs, x, N, trials, rng):
    dim = len(probs)
    fails = 0
    for _ in range(trials):
        samples = rng.choice(dim, size=N, p=probs)
        counts = np.bincount(samples, minlength=dim)
        if int(np.argmax(counts)) != x:
            fails += 1
    return fails / trials


def main():
    rng = np.random.default_rng(2)
    eps = 0.10
    print(f"=== Theorem 2 verification (corrected union-bound), eps={eps} ===\n")
    print(f"{'n':>3}{'p_max':>8}{'p_2nd':>8}{'gamma':>8}{'N_correct':>10}{'fail':>8}{'ok':>5}")
    print("-" * 52)
    configs = [(6, 3, 5), (8, 2, 3), (8, 3, 8), (8, 3, 4), (10, 3, 10)]
    for n, deg, terms in configs:
        dim = 1 << n
        x = int(rng.integers(dim))
        g = random_anf_function(n, degree=deg, num_terms=terms,
                                seed=int(rng.integers(10000)))
        probs = run_bv_attack(n, x, g)
        order = np.sort(probs)[::-1]
        p_max, p_2 = order[0], order[1]
        gamma = p_max - p_2
        if gamma < 1e-9:
            print(f"{n:>3}{p_max:>8.4f}{p_2:>8.4f}{gamma:>8.4f}   SKIP (SAI>1)")
            continue
        N = int(np.ceil((2 / gamma**2) * (n * np.log(2) + np.log(1 / eps))))
        fr = full_fail(probs, x, N, 3000, rng)
        print(f"{n:>3}{p_max:>8.4f}{p_2:>8.4f}{gamma:>8.4f}{N:>10}"
              f"{fr:>8.4f}{'YES' if fr <= eps else 'NO':>5}")

    print("\n=== Why the OLD (2/gamma^2)ln(4/eps) bound is not a valid guarantee ===")
    print("The old bound is CONSTANT in the number of competitors K near the mode,")
    print("but by the union bound the failure probability grows with K. So the old")
    print("form provides no high-probability guarantee: for a fixed gamma, the N it")
    print("prescribes does not increase with K, while the N actually required does.\n")
    gamma = 0.05
    print(f"  gamma fixed at {gamma}, eps={eps}")
    print(f"  {'K':>6} {'N_old':>10} {'N_union':>10} {'ratio':>7}")
    for K in [2, 4, 16, 64, 256, 1024]:
        N_old = int(np.ceil((2 / gamma**2) * np.log(4 / eps)))
        N_uni = int(np.ceil((2 / gamma**2) * np.log(K / eps)))
        print(f"  {K:>6} {N_old:>10} {N_uni:>10} {N_uni / N_old:>7.2f}")
    print("\n  The old bound's N is flat; the required N grows like ln(K). Theorem 2's")
    print("  n*ln2 term is exactly this union-bound factor (K <= 2^n competitors),")
    print("  making the bound valid for ALL noise functions. On benign small-n g the")
    print("  omission is harmless, which is why naive use appears to work in practice.")


if __name__ == "__main__":
    main()

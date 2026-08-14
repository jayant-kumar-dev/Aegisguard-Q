"""
hb_superposition_sim.py

Simulates the Bernstein-Vazirani based superposition attack on the HB
authentication protocol (Algorithm 2, Cid-Elkouss-Goulao 2026), and extends
it to test the paper's open question: does the attack survive when the
noise e = g_s(a) is a deterministic function of the challenge 'a' rather
than an independent Bernoulli sample?

This is a pure numpy statevector simulation (no quantum SDK dependency) --
exact for the small n we use, and directly mirrors the linear-algebra
identities in the paper (Walsh-Hadamard transform = H^{\\otimes n}).

Usage:
    python3 hb_superposition_sim.py
"""

import numpy as np
import itertools
import random


# ----------------------------------------------------------------------
# Core primitives
# ----------------------------------------------------------------------

def popcount_mod2(v: int) -> int:
    """Parity of bit-string v (i.e. a . x style dot products, once ANDed)."""
    return bin(v).count("1") % 2


def walsh_hadamard_transform(vec: np.ndarray) -> np.ndarray:
    """
    In-place-style fast Walsh-Hadamard transform.
    Equivalent to applying H^{\\otimes n} to a length-2^n state vector.
    """
    a = vec.copy()
    n_dim = len(a)
    h = 1
    while h < n_dim:
        for i in range(0, n_dim, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j], a[j + h] = x + y, x - y
        h *= 2
    return a / np.sqrt(n_dim)


def build_phase_oracle(n: int, x: int, noise_fn) -> np.ndarray:
    """
    Builds the phase vector for oracle O: |a> -> (-1)^{a.x XOR e(a)} |a>

    noise_fn(a) -> 0/1, allowed to depend on 'a' (deterministic-LPN case)
    or ignore 'a' and use external randomness (standard Bernoulli case).
    """
    dim = 1 << n
    phases = np.empty(dim, dtype=np.float64)
    for a in range(dim):
        dot = popcount_mod2(a & x)
        e = noise_fn(a)
        phases[a] = (-1.0) ** (dot ^ e)
    return phases


def run_bv_attack(n: int, x: int, noise_fn) -> np.ndarray:
    """
    Runs the full BV circuit: uniform superposition -> phase oracle -> WHT.
    Returns probability distribution over measurement outcomes (length 2^n).
    """
    dim = 1 << n
    uniform = np.ones(dim) / np.sqrt(dim)          # after first H^{\\otimes n}
    phased = uniform * build_phase_oracle(n, x, noise_fn)   # oracle applied
    final_amp = walsh_hadamard_transform(phased)     # second H^{\\otimes n}
    probs = np.abs(final_amp) ** 2
    return probs


# ----------------------------------------------------------------------
# Noise models
# ----------------------------------------------------------------------

def make_bernoulli_noise(tau: float):
    """Standard HB: e sampled once, independent of 'a' (paper's Algorithm 2)."""
    e = 1 if random.random() < tau else 0
    return lambda a: e


def make_linear_deterministic_noise(s: int):
    """e = a . s  (a second secret) -- deterministic but still LINEAR in a."""
    return lambda a: popcount_mod2(a & s)


def make_nonlinear_deterministic_noise(n: int, num_and_terms: int, seed=None):
    """
    e = XOR of `num_and_terms` random 2-bit AND terms of 'a'.
    num_and_terms controls the algebraic degree / nonlinearity of g.
    num_and_terms = 0 -> constant (degree 0)
    """
    rng = random.Random(seed)
    terms = []
    for _ in range(num_and_terms):
        i, j = rng.sample(range(n), 2)
        terms.append((i, j))

    def g(a: int) -> int:
        val = 0
        for (i, j) in terms:
            bi = (a >> i) & 1
            bj = (a >> j) & 1
            val ^= (bi & bj)
        return val

    return g


# ----------------------------------------------------------------------
# Experiments
# ----------------------------------------------------------------------

def experiment_baseline(n=8, trials=20):
    """Reproduce paper's claim: 1-query recovery regardless of tau."""
    print("=== Experiment 1: Baseline (Bernoulli noise, Algorithm 2) ===")
    for tau in [0.05, 0.15, 0.25, 0.45]:
        successes = 0
        for _ in range(trials):
            x = random.randrange(1 << n)
            probs = run_bv_attack(n, x, make_bernoulli_noise(tau))
            recovered = int(np.argmax(probs))
            successes += (recovered == x) and np.isclose(probs[x], 1.0)
        print(f"  tau={tau:.2f}: {successes}/{trials} exact single-query recoveries "
              f"(P(x) should == 1.0 always)")
    print()


def experiment_linear_deterministic(n=8, trials=10):
    """Deterministic but linear noise: attack still succeeds, recovers x XOR s."""
    print("=== Experiment 2: Linear deterministic noise e = a.s ===")
    for _ in range(trials):
        x = random.randrange(1 << n)
        s = random.randrange(1 << n)
        probs = run_bv_attack(n, x, make_linear_deterministic_noise(s))
        recovered = int(np.argmax(probs))
        target = x ^ s
        ok = (recovered == target) and np.isclose(probs[target], 1.0)
        print(f"  x={x:0{n}b} s={s:0{n}b} -> recovered {recovered:0{n}b} "
              f"(expected x XOR s = {target:0{n}b})  match={ok}")
    print("  => Linear deterministic noise does NOT protect the secret;")
    print("     it just shifts what's recovered. Full x recoverable if s known/guessable.\n")


def experiment_nonlinear_sweep(n=10, trials_per_level=8):
    """
    Core new result: sweep nonlinearity of g and measure how P(recover x)
    degrades. This is the paper's open question, made quantitative.
    """
    print("=== Experiment 3: Nonlinear deterministic noise sweep ===")
    print(f"  (n={n} qubits, {trials_per_level} random trials per nonlinearity level)\n")
    print(f"  {'AND terms':>10} | {'avg P(x)':>10} | {'avg P(argmax)':>14} | {'argmax==x rate':>15}")
    print("  " + "-" * 58)

    for num_terms in [0, 1, 2, 4, 8, 16]:
        px_vals = []
        pmax_vals = []
        hit_count = 0
        for trial in range(trials_per_level):
            x = random.randrange(1 << n)
            g = make_nonlinear_deterministic_noise(n, num_terms, seed=None)
            probs = run_bv_attack(n, x, g)
            px_vals.append(probs[x])
            argmax = int(np.argmax(probs))
            pmax_vals.append(probs[argmax])
            hit_count += (argmax == x)
        print(f"  {num_terms:>10} | {np.mean(px_vals):>10.4f} | "
              f"{np.mean(pmax_vals):>14.4f} | {hit_count}/{trials_per_level:<13}")
    print()
    print("  Interpretation: num_terms=0 reduces to linear/Bernoulli case (P(x)=1).")
    print("  As nonlinearity increases, watch whether P(x) decays toward 1/2^n")
    print("  (fully protected) or plateaus above baseline (partial leak survives).")


if __name__ == "__main__":
    random.seed(42)
    experiment_baseline(n=8, trials=20)
    experiment_linear_deterministic(n=8, trials=5)
    experiment_nonlinear_sweep(n=10, trials_per_level=10)

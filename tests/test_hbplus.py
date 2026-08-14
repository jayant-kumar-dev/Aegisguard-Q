"""
HB+ extension. In HB+ the reader sends challenge a, the tag sends a blinding b,
and the response is z = a.x XOR b.y XOR e, with secrets x, y in {0,1}^n.

Q2 model: the adversary queries an oracle over the joint register |a>|b>.
Phase oracle: |a>|b> -> (-1)^{a.x XOR b.y XOR g(a,b)} |a>|b>, where g is the
(possibly deterministic) noise as a function of the 2n-bit input (a,b).

Question: does Lemma 1 generalize? I.e. is
   P(measure = (wa, wb)) = W_G((wa XOR x, wb XOR y))^2 / 4^(2n)  ?
where G(a,b) = g(a,b) is treated as a Boolean function on 2n bits, and
W_G is its Walsh transform on {0,1}^{2n}.

If so, then a single BV circuit on the 2n-qubit register recovers (x,y)
jointly by exactly the same argument -- Lemma 1 generalizes verbatim with
n -> 2n and the linear part a.x XOR b.y being the inner product of the
concatenated (a,b) with the concatenated (x,y).

Runs both as a pytest module (`pytest tests/test_hbplus.py`) and as a
standalone script (`python tests/test_hbplus.py`).
"""
import numpy as np


def popcount_mod2(v):
    return bin(v).count("1") & 1


def fwht(vec):
    a = vec.copy()
    dim = len(a)
    h = 1
    while h < dim:
        for i in range(0, dim, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j] = x + y
                a[j + h] = x - y
        h *= 2
    return a


def run_bv_2n(n, x, y, g):
    """BV on 2n qubits. index = a*2^n + b (a high bits, b low bits)."""
    N = 2 * n
    dim = 1 << N
    signs = np.empty(dim)
    for idx in range(dim):
        a = idx >> n
        b = idx & ((1 << n) - 1)
        e = g(a, b)
        phase = (popcount_mod2(a & x) ^ popcount_mod2(b & y) ^ e)
        signs[idx] = -1.0 if phase else 1.0
    uniform = np.ones(dim) / np.sqrt(dim)
    phased = uniform * signs
    final = fwht(phased) / np.sqrt(dim)
    return np.abs(final) ** 2


def walsh_2n(n, g):
    N = 2 * n
    dim = 1 << N
    signs = np.empty(dim)
    for idx in range(dim):
        a = idx >> n
        b = idx & ((1 << n) - 1)
        signs[idx] = -1.0 if g(a, b) else 1.0
    return fwht(signs)


def test_bernoulli_joint_recovery():
    """Standard Bernoulli noise (once per call, independent of a,b): the joint
    secret (x,y) is recovered with probability 1 by a single BV query on the
    2n-qubit register -- the noise is a global phase (Lemma 1')."""
    n = 4
    rng = np.random.default_rng(0)
    x = int(rng.integers(1 << n))
    y = int(rng.integers(1 << n))
    r_bit = int(rng.integers(2))
    g_bern = lambda a, b, r=r_bit: r
    probs = run_bv_2n(n, x, y, g_bern)
    target = (x << n) | y
    assert int(np.argmax(probs)) == target
    assert abs(probs[target] - 1.0) < 1e-12


def test_generalized_lemma1():
    """For a deterministic g(a,b), the measured BV distribution matches the
    generalized identity P(w) = W_g(w XOR (x,y))^2 / 4^(2n) exactly -- Lemma 1'
    holds to floating-point precision."""
    n = 4
    rng = np.random.default_rng(0)
    x = int(rng.integers(1 << n))
    y = int(rng.integers(1 << n))
    g_det = lambda a, b: ((a >> 0) & 1) & ((b >> 1) & 1)  # nonlinear joint function
    probs = run_bv_2n(n, x, y, g_det)
    W = walsh_2n(n, g_det)
    dim = 1 << (2 * n)
    probs_theory = np.empty(dim)
    for idx in range(dim):
        wa = idx >> n
        wb = idx & ((1 << n) - 1)
        u = ((wa ^ x) << n) | (wb ^ y)
        probs_theory[idx] = W[u] ** 2 / (dim ** 2)
    err = float(np.max(np.abs(probs - probs_theory)))
    assert err < 1e-9


if __name__ == "__main__":
    # Standalone script mode (matches the paper's "script test_hbplus.py").
    n = 4
    rng = np.random.default_rng(0)
    x = int(rng.integers(1 << n))
    y = int(rng.integers(1 << n))
    r_bit = int(rng.integers(2))
    g_bern = lambda a, b, r=r_bit: r
    probs = run_bv_2n(n, x, y, g_bern)
    target = (x << n) | y
    print("Test 1 (Bernoulli): recovered idx == (x,y)?",
          int(np.argmax(probs)) == target, " P=", probs[target])

    g_det = lambda a, b: ((a >> 0) & 1) & ((b >> 1) & 1)
    probs = run_bv_2n(n, x, y, g_det)
    W = walsh_2n(n, g_det)
    dim = 1 << (2 * n)
    probs_theory = np.empty(dim)
    for idx in range(dim):
        wa = idx >> n
        wb = idx & ((1 << n) - 1)
        u = ((wa ^ x) << n) | (wb ^ y)
        probs_theory[idx] = W[u] ** 2 / (dim ** 2)
    err = float(np.max(np.abs(probs - probs_theory)))
    print("Test 2 (generalized Lemma 1): max|P_sim - P_theory| =",
          f"{err:.2e}", "-> identity holds" if err < 1e-9 else "MISMATCH")

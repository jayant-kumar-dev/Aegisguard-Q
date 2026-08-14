# AegisGuard-Q

**Quantum-leakage static analysis for deterministic-noise HB-style authentication protocols.**

AegisGuard-Q takes a deterministic Boolean noise function `g: {0,1}ⁿ → {0,1}`, computes its Walsh spectrum, and reports how much a quantum adversary can learn about the secret key of an HB-style authentication protocol that uses `g` as its noise source — together with an estimate of how many quantum queries a key-recovery attack would need, and whether the choice of `g` is even usable as a classical protocol.

It is the reference implementation accompanying the paper *Spectral Characterization of Superposition Leakage in Deterministic-LPN Authentication Protocols*.

---

## Why this exists

Cid, Elkouss & Goulão (IACR CiC, 2026) showed that the **HB, HB+, and HB#** lightweight authentication protocols — whose classical security rests on the Learning Parity with Noise (LPN) problem — are broken in a *single* quantum query when an attacker can query the prover in superposition (the "Q2" model). The reason is elegant: the protocols' independent Bernoulli noise becomes an unobservable **global phase** under a superposition query, so the Bernstein-Vazirani algorithm recovers the key as if there were no noise at all.

That paper left an explicit **open question**: what if the noise is *deterministic* — computed as `e = g(a)` for some fixed Boolean function `g`, instead of sampled randomly? Then the noise is no longer a global phase, and the one-query attack does not obviously apply.

**AegisGuard-Q answers that question.** It shows the security of a deterministic-noise variant is governed entirely by the **Walsh spectrum** of `g`, and turns that into a concrete, computable risk report.

---

## What it tells you

Given `g`, AegisGuard-Q classifies it into one of four leakage classes and quantifies the attack:

| Class | Condition | What it means | Risk |
|---|---|---|---|
| **AFFINE** | unique spectral peak, `Nl(g)=0` | secret recovered in **O(1)** queries | CRITICAL |
| **GENERIC** | unique spectral peak, nonlinear | secret recovered in a bounded number of queries (computed) | HIGH |
| **PARTIAL** | several tied spectral peaks | secret narrowed to a small, computable coset — not a point | MEDIUM |
| **BENT** | perfectly flat spectrum | **zero** single-query leakage | LOW |

It also computes:

- **SAI** (Spectral Ambiguity Index) — how many key candidates the attack narrows to,
- **query complexity** — how many quantum queries a recovery attack needs (via a Goldreich-Levin bound),
- **the completeness–leakage trade-off** — bent functions defeat the quantum attack, but the same flatness forces the classical noise rate toward 0.5, which breaks the protocol's honest-user acceptance. **You cannot have both.**

---

## Install

The **core tool has zero dependencies** — pure Python standard library (3.9+). Nothing to install to use it:

```bash
python -m aegisguard_q.cli --family bent --n 8 --format markdown
```

Or install it as a package (adds the `aegisguard-q` command):

```bash
pip install .
```

To run the test suite and the statevector cross-validation, install the test extras:

```bash
pip install -e ".[test]"     # or: pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## Quick start

**As a library:**

```python
from aegisguard_q import analyze_noise_function, noise_functions as nf, to_markdown

# Analyze a bent noise function on n=8 bits
report = analyze_noise_function(8, nf.bent_inner_product(8))
print(to_markdown(report))
```

**As a command-line tool:**

```bash
# A bent function: safe against the single-query attack (but see the trade-off)
python -m aegisguard_q.cli --family bent --n 8

# An affine function: catastrophic — recovered in one query
python -m aegisguard_q.cli --family affine --n 8

# A random nonlinear function: recovered, but needs many queries
python -m aegisguard_q.cli --family anf --n 8 --degree 3 --terms 9 --format json
```

Example output (bent, `n=8`): leakage class **BENT**, SAI **256**, `Δ_prob = 0`, completeness bound `|0.5 − τ| ≤ 0.03125` — i.e. the attack learns nothing, but the noise rate is forced to ≈0.47, which is protocol-breaking. For an **affine** function on the same `n`: class **AFFINE**, SAI **1**, recovery probability **1.0** — the key falls out in a single query.

---

## How it works

1. **Walsh transform.** For `g` on `n` bits, compute `Ŵ_g(u) = Σₐ (−1)^{g(a) ⊕ a·u}` via an in-house fast Walsh-Hadamard transform (`O(n·2ⁿ)`).
2. **Specialization (Lemma 1).** For the HB oracle `h(a) = a·x ⊕ g(a)`, the measured BV distribution is `P(w) = Ŵ_g(x⊕w)² / 4ⁿ`. So the attacker's outcome distribution is just `g`'s spectrum, shifted by the secret.
3. **Read off the metrics.** The location(s) of the spectral peak(s) determine SAI and the leakage class; the peak-to-runner-up gap determines the query complexity; `Ŵ_g(0)` determines the classical noise rate and the completeness bound.

Everything is exact for `n ≤ 24`.

---

## Reproducibility

Every claim in the paper is checkable by running the tests:

- `tests/test_core.py` — asserts the closed-form identities (affine ⇒ SAI=1; bent ⇒ SAI=2ⁿ, `Δ=0`, and the completeness equality `|0.5−τ| = 2^(−n/2−1)`; Parseval; recovery probability = `Ŵ_g(0)²/4ⁿ`), **and cross-validates** the tool against an independent NumPy statevector simulator to floating-point precision.
- `tests/test_hbplus.py` — verifies the HB+ (two-secret) extension.
- `verify_theorem2.py` — empirically confirms the query-complexity bound (and demonstrates why a naive earlier version of the bound was wrong).

```bash
python -m pytest tests/ -v      # 12 tests
python verify_theorem2.py
```

---

## Repository layout

```
aegisguard_q/
├── aegisguard_q/          # the package (zero-dependency core)
│   ├── core.py            #   Walsh engine + leakage analysis
│   ├── noise_functions.py #   affine / linear / random-ANF / bent constructors
│   ├── report.py          #   JSON + markdown report export
│   └── cli.py             #   command-line interface
├── tests/                 # regression + cross-validation suite
├── verify_theorem2.py     # standalone query-complexity verification
├── hb_superposition_sim*.py  # independent statevector simulators (for cross-check)
├── paper.tex              # the accompanying manuscript source
├── requirements.txt       # test/simulator deps (numpy, pytest)
└── pyproject.toml         # packaging (core deps: none)
```

---

## Scope and limitations

This is a **research characterization and tool**, built on established techniques (Walsh/Fourier sampling and the quantum Goldreich-Levin algorithm), applied to a setting where they had not been applied before. It is deliberately explicit about what it does *not* establish:

- It does **not** establish the *classical* hardness of deterministic-LPN variants — replacing Bernoulli noise with `g(a)` forfeits the standard LPN security reduction, and whether these variants are classically secure is an open problem.
- HB+ (two secrets) is handled; **HB#** (matrix secrets) and **adaptive** adversaries are natural next steps, not yet covered.
- The results assume the standard Q2 noise model (noise sampled once per oracle call, independent of the coherent input).

See the paper's Limitations section for the full list.

---

## Citing

If you use AegisGuard-Q, please cite the accompanying manuscript (see `paper.tex`) and the foundational work it builds on: Cid, Elkouss & Goulão, *Superposition Attacks Against LPN-Based Authentication Protocols*, IACR Communications in Cryptology 3(1), 2026, https://doi.org/10.62056/abhey7n4e.

## License

MIT.

---

## Version 2.0 — information-theoretic layer

Version 2.0 adds the quantities used in the accompanying manuscript:

| Function | Manuscript reference | What it computes |
|---|---|---|
| `mutual_information(n, g)` | Theorem 2 | `I(X;W) = n − H(P_g)`, exact, in bits |
| `translation_stabilizer(n, g)` | Definition 5 / Theorem 7 | `Stab(P_g)`; the secret is identifiable from unlimited queries iff this is `{0}` |
| `spectral_ambiguity_index(n, g)` | Definition 6 | number of tied spectral maxima |
| `probability_gap(n, g)` | Theorem 8 | mode gap `γ = p₁ − p₂` (0 if no unique mode) |
| `empirical_mode_bound(n, γ, ε)` | Theorem 8 | `N ≥ (2/γ²)(n ln 2 + ln(1/ε))` |
| `noise_functions.semibent_odd(n)` | Section 11 | odd-`n` benchmark; no bent function exists for odd `n` |

### Reproducing the manuscript tables

```bash
python experiments.py
```

This regenerates Table 1 and Table 2 exactly. All pseudorandom instances use
fixed documented seeds (`RANDOM_SEEDS = {4: 10, 6: 2, 8: 10}`); the `n=6` seed
is chosen so the instance has a unique spectral mode, the regime where the
empirical-mode bound applies. The driver also asserts the manuscript's
closed-form predictions on every row and exits non-zero if any fails.

```bash
python -m pytest tests/ -v     # 25 tests
```

### Citing

See `CITATION.cff`. Cite both the software (this repository, version 2.0.0)
and the manuscript, *Spectral Characterization of Superposition Leakage in
Deterministic-LPN Authentication Protocols*, Version 1.0, August 2026.

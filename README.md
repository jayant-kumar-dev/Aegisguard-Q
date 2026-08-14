# AegisGuard-Q

**Quantum-leakage static analysis for deterministic-noise HB-style authentication protocols.**

AegisGuard-Q takes a deterministic Boolean noise function `g: {0,1}ⁿ → {0,1}` and computes, exactly, how much a quantum adversary learns about the secret key of an HB-style authentication protocol that uses `g` as its noise source — how many bits leak from a single superposition query, what remains identifiable after unlimited queries, how many queries a recovery attack needs, and whether the choice of `g` is even usable as classical noise.

It is the reference implementation accompanying the manuscript *Spectral Characterization of Superposition Leakage in Deterministic-LPN Authentication Protocols* (Version 1.0, August 2026), included here as `paper.tex`.

---

## Why this exists

Cid, Elkouss & Goulão (*IACR Communications in Cryptology* 3(1), 2026) showed that the **HB**, **HB+** and **HB#** lightweight authentication protocols — whose classical security rests on Learning Parity with Noise (LPN) — fall to a *single* quantum query when the prover can be queried in superposition (the "Q2" model). The mechanism is elegant: the protocols' independently sampled Bernoulli noise becomes an unobservable **global phase** under a coherent query, so Bernstein-Vazirani recovers the key as though there were no noise at all.

That paper left an explicit **open question**: what if the noise is *deterministic* — computed as `e = g(a)` for a fixed Boolean function `g` — so that it is no longer a global phase?

**AegisGuard-Q characterizes the quantum side of that question.** The central result is that the Q2 measurement distribution is exactly a *translation* of the squared Walsh spectrum of `g`, shifted by the secret. Everything else — leakage in bits, identifiability, query complexity — follows from the spectrum.

> **Scope warning, stated up front.** With a *public* `g`, the construction is classically broken outright: an adversary computes `z ⊕ g(a) = a·x` and recovers the secret by Gaussian elimination, no LPN hardness required. This tool is designer-side analysis of Q2 leakage structure and groundwork for **keyed** variants `g_s`, **not** a security proof for a deployable protocol. See [Scope and limitations](#scope-and-limitations).

---

## The theory in one screen

For secret `x` and known noise function `g`, the HB-style phase oracle is

```
O|a⟩ = (−1)^(a·x ⊕ g(a)) |a⟩
```

Write the unnormalized Walsh transform and the induced measurement distribution as

```
W_g(u) = Σ_a (−1)^(g(a) ⊕ a·u)          P_g(u) = W_g(u)² / 4ⁿ
```

| Result | Statement |
|---|---|
| **Lemma 1** (Walsh shift) | `W_h(w) = W_g(w ⊕ x)`, hence `Pr[W = w \| X = x] = P_g(w ⊕ x)` |
| **Theorem 2** (leakage) | `I(X;W) = n − H(P_g)` — exact mutual information, in bits |
| **Corollary 3** (affine) | affine `g` ⇒ point mass ⇒ `I = n`, secret recovered in one query |
| **Corollary 4** (bent) | bent `g` (needs even `n`) ⇒ uniform `P_g` ⇒ `I = 0` |
| **Theorem 7** (identifiability) | `x` is identifiable from unlimited queries **iff** `Stab(P_g) = {0}` |
| **Theorem 8** (sample complexity) | unique mode ⇒ `N ≥ (2/γ²)(n ln 2 + ln(1/ε))` suffices |
| **Theorem 9** (trade-off) | `\|1 − 2τ\| ≤ λ`, where `λ = max\|W_g\|/2ⁿ` and `τ = wt(g)/2ⁿ` |

The last one is the design tension: flattening the spectrum is exactly what defeats the Q2 attack, and it is exactly what forces the classical noise rate `τ` toward 1/2. **You cannot have both.**

Two normalizations that are easy to confuse: `λ = max|W_g|/2ⁿ` is an *amplitude*; `p_max = max P_g = λ²` is a *probability*. The mode gap `γ` is a difference of probabilities.

---

## Install

The **core library has zero dependencies** — pure Python standard library (3.9+):

```bash
python -m aegisguard_q.cli --family bent --n 8 --format markdown
```

Install as a package (adds the `aegisguard-q` command):

```bash
pip install .
```

For the test suite, the statevector cross-validation, and the experiment driver:

```bash
pip install -e ".[test]"      # or: pip install -r requirements.txt
```

---

## Quick start

**As a library:**

```python
from aegisguard_q import (
    analyze_noise_function, mutual_information,
    translation_stabilizer, noise_functions as nf, to_markdown,
)

g = nf.bent_inner_product(8)

print(to_markdown(analyze_noise_function(8, g)))
print("leakage:", mutual_information(8, g), "bits")
print("stabilizer size:", len(translation_stabilizer(8, g)))
```

**As a command-line tool:**

```bash
# Bent: zero single-query leakage — but see the trade-off
python -m aegisguard_q.cli --family bent --n 8

# Affine: catastrophic, key falls out in one query
python -m aegisguard_q.cli --family affine --n 8

# Random nonlinear: recovered, but needs many queries
python -m aegisguard_q.cli --family anf --n 8 --degree 3 --terms 9 --format json
```

---

## API reference

### Core (`aegisguard_q.core`)

| Function | Returns |
|---|---|
| `walsh_spectrum(n, g)` | raw Walsh coefficients `W_g(u)`, via in-house FWHT, `O(n·2ⁿ)` |
| `fast_walsh_hadamard(vec)` | the transform itself |
| `hamming_weight(n, g)` | number of inputs where `g(a) = 1` |
| `analyze_noise_function(n, g, epsilon)` | full `LeakageReport`: class, SAI, gap, entropy, `τ`, nonlinearity, query complexity |

### Information-theoretic layer (`aegisguard_q.information`) — v2.0

| Function | Paper reference | Computes |
|---|---|---|
| `spectral_distribution(n, g)` | §4 | `P_g(u) = W_g(u)²/4ⁿ` |
| `shannon_entropy(p)` | §5 | `H(P) = −Σ P log₂ P` |
| `mutual_information(n, g)` | Theorem 2 | `I(X;W) = n − H(P_g)`, in bits |
| `translation_stabilizer(n, g)` | Definition 5 / Theorem 7 | `Stab(P_g)` as a sorted list; `{0}` ⟺ identifiable |
| `spectral_ambiguity_index(n, g)` | Definition 6 | number of tied spectral maxima |
| `probability_gap(n, g)` | Theorem 8 | `γ = p₁ − p₂`, or `0` if no unique mode |
| `empirical_mode_bound(n, γ, ε)` | Theorem 8 | `N ≥ (2/γ²)(n ln 2 + ln(1/ε))`, `None` if `γ = 0` |
| `max_normalized_walsh(n, g)` | Theorem 9 | `λ = max\|W_g\|/2ⁿ` |

### Benchmark constructors (`aegisguard_q.noise_functions`)

| Function | Notes |
|---|---|
| `affine(n, s, c)` | `g(a) = a·s ⊕ c` |
| `linear(n, s)` | `g(a) = a·s` |
| `random_anf(n, degree, num_terms, seed)` | XOR of random monomials; controls algebraic degree |
| `bent_inner_product(n)` | Maiorana–McFarland, **requires even `n`** |
| `semibent_odd(n)` | **requires odd `n`** — extends a bent function on `n−1` variables; no bent function exists in odd dimension |

`SAI` and `|Stab|` are **different quantities**: the first counts tied maxima, the second measures translation symmetry of the whole distribution. A distribution can have tied maxima and still a trivial stabilizer — see the `n = 8` random row below.

---

## Reproducing the manuscript tables

```bash
python experiments.py
```

This regenerates **both tables exactly** and asserts the closed-form predictions of Theorems 2, 8 and 9 on every row, exiting non-zero on any mismatch.

### Table 1 — exact spectral metrics

| Family | n | τ | λ | H | MI | \|S\| | SAI | γ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affine | 4 | 0.5000 | 1.0000 | 0.0000 | 4.0000 | 1 | 1 | 1.0000 |
| Bent | 4 | 0.3750 | 0.2500 | 4.0000 | 0.0000 | 16 | 16 | 0 |
| Random | 4 | 0.3750 | 0.5000 | 3.0000 | 1.0000 | 2 | 2 | 0 |
| Affine | 6 | 0.5000 | 1.0000 | 0.0000 | 6.0000 | 1 | 1 | 1.0000 |
| Bent | 6 | 0.4375 | 0.1250 | 6.0000 | 0.0000 | 64 | 64 | 0 |
| Random | 6 | 0.5156 | 0.3438 | 4.9959 | 1.0041 | 1 | 1 | 0.0391 |
| Affine | 8 | 0.5000 | 1.0000 | 0.0000 | 8.0000 | 1 | 1 | 1.0000 |
| Bent | 8 | 0.4688 | 0.0625 | 8.0000 | 0.0000 | 256 | 256 | 0 |
| Random | 8 | 0.4453 | 0.1875 | 6.8601 | 1.1399 | 1 | 1 | 0.0056 |
| Odd-semibent | 3 | 0.2500 | 0.5000 | 2.0000 | 1.0000 | 4 | 4 | 0 |
| Odd-semibent | 5 | 0.3750 | 0.2500 | 4.0000 | 1.0000 | 16 | 16 | 0 |
| Odd-semibent | 7 | 0.4375 | 0.1250 | 6.0000 | 1.0000 | 64 | 64 | 0 |

`λ = max|W_g|/2ⁿ` · `H` = spectral measurement entropy · `MI = I(X;W)` · `|S| = |Stab(P_g)|` · `γ` = mode gap.

Reading it: **affine** leaks all `n` bits and is fully identifiable. **Bent** leaks nothing and the stabilizer is everything — no number of repetitions helps. **Odd-semibent** sits exactly in between at one bit, leaving a `2^(n−1)`-element equivalence class, which is the sharpest illustration that "no leakage" and "identifiable" are separate axes.

### Table 2 — empirical mode failure (seeded random `n = 6`, γ = 0.0390625, ε = 0.05, Theorem 8 bound `N ≥ 9378`)

| N | Failure rate |
|---:|---:|
| 250 | 0.0963 |
| 500 | 0.0273 |
| 1000 | 0.0003 |
| 2000 | 0.0003 |
| 5000 | 0.0000 |
| 9378 | 0.0000 |

The bound is conservative on this instance, as expected from the union bound.

### Frozen experimental parameters

| Parameter | Value |
|---|---|
| Benchmark seeds (`n = 4, 6, 8`) | `10`, `2`, `10` — the `n=6` seed chosen so the instance has a unique spectral mode |
| Monte-Carlo generator seed | `20260814` |
| Trials per `N` | `3000` |
| `ε` | `0.05` |
| Python / NumPy / pytest | 3.12.3 / 2.4.4 / 9.1.1 |

---

## Tests

```bash
python -m pytest tests/ -v      # 25 tests
python verify_theorem2.py       # standalone query-complexity verification
```

| File | Covers |
|---|---|
| `tests/test_core.py` | closed-form identities (affine ⇒ SAI 1, recovery probability 1; bent ⇒ SAI `2ⁿ`, `Δ = 0`, `\|τ − ½\| = 2^(−n/2−1)`; Parseval; `P(recover) = W_g(0)²/4ⁿ`), plus cross-validation against an independent NumPy statevector simulator to floating-point precision |
| `tests/test_hbplus.py` | the HB+ two-secret joint-input extension |
| `tests/test_information.py` | Parseval, affine/bent/odd-semibent endpoints, the `MI = n − H` identity on arbitrary instances, the Theorem 9 bound, stabilizer subgroup closure, and the `N = 9378` bound formula |
| `verify_theorem2.py` | confirms the corrected bound empirically and shows why a version constant in the number of near-tied competitors is not a valid guarantee |

---

## How it works

1. **Walsh transform.** Compute `W_g(u)` by in-house fast Walsh-Hadamard transform in `O(n·2ⁿ)`.
2. **Specialization (Lemma 1).** The BV measurement distribution is `P_g(x ⊕ w)` — the spectrum, shifted by the secret. The attacker's outcome distribution *is* the spectrum.
3. **Read off the metrics.** Entropy gives leakage in bits; translation symmetry gives identifiability; the peak-to-runner-up gap gives query complexity; `W_g(0)` gives the classical noise rate and the trade-off bound.

Exact for `n ≤ 24` (`2²⁴` floats). Beyond that the tool raises rather than silently exhausting memory; sampling-based analysis would be required.

---

## Repository layout

```
.
├── aegisguard_q/            # the package (zero-dependency core)
│   ├── core.py              #   Walsh engine + leakage report
│   ├── information.py       #   MI, stabilizer, SAI, gap, mode bound   [v2.0]
│   ├── noise_functions.py   #   affine / linear / random-ANF / bent / semibent
│   ├── report.py            #   JSON + markdown export
│   └── cli.py               #   command-line interface
├── tests/                   # 25 tests: regression + cross-validation
├── experiments.py           # regenerates Tables 1 and 2                [v2.0]
├── verify_theorem2.py       # standalone query-complexity verification
├── hb_superposition_sim*.py # independent statevector simulators
├── paper.tex                # accompanying manuscript source
├── CITATION.cff             # citation metadata
├── requirements.txt         # test/simulator deps (numpy, pytest)
└── pyproject.toml           # packaging (core deps: none)
```

---

## Scope and limitations

This is a **research characterization and tool**, built on established techniques (Walsh/Fourier sampling, quantum Goldreich-Levin) applied to a setting where they had not been applied before. It is deliberately explicit about what it does *not* establish:

- **With a public `g`, the construction is classically broken outright** by Gaussian elimination — no LPN hardness needed. The object of study is Q2 leakage structure, not a deployable protocol. Classical hardness is open only for **keyed / secret-`g`** variants `e = g_s(a)`, where that linear-algebra recovery no longer applies.
- **Theorem 8 is a statistical upper bound, not a polynomial-query security statement.** If `γ` is exponentially small the required `N` can be exponential; polynomial-query recovery needs an inverse-polynomial lower bound on `γ`.
- **The HB+ section is an idealized joint-input extension**, not a protocol-level attack. A real attack would require coherently representing the message flow and the source of the blinding vector `b`.
- **HB#** (matrix secrets) and **adaptive** adversaries are natural next steps, not yet covered.
- Results assume the standard Q2 noise model: noise sampled once per oracle call, independent of the coherent input.
- **No priority claim is made.** The literature survey in the manuscript is systematic and every reference checked, but no search certifies novelty; independent review by a subject-area specialist remains appropriate.

---

## Citing

See `CITATION.cff` — GitHub renders a "Cite this repository" button from it.

Please cite **both** the software and the manuscript:

> Kumar, J. (2026). *AegisGuard-Q: Quantum-leakage static analysis for deterministic-LPN noise functions*, version 2.0.0. https://github.com/jayant-kumar-dev/Aegisguard-Q

> Kumar, J. (2026). *Spectral Characterization of Superposition Leakage in Deterministic-LPN Authentication Protocols*, Version 1.0.

<!-- After the Zenodo deposit, add the DOI here and in CITATION.cff. -->

And the foundational work this builds on:

> Cid, C., Elkouss, D., & Goulão, M. (2026). Superposition Attacks Against LPN-Based Authentication Protocols. *IACR Communications in Cryptology*, 3(1):17. https://doi.org/10.62056/abhey7n4e

---

## License

MIT.

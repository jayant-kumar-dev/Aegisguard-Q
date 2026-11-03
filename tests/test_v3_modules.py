import math

from aegisguard_q import analyze_noise_function
from aegisguard_q import noise_functions as nf
from aegisguard_q.keyed_dlpn import key_invariance_check, profile_keyed_family
from aegisguard_q.nisq_channel import noisy_channel_metrics, noisy_spectral_distribution
from aegisguard_q.protocols import hbplus_entangled_b_leakage, hbsharp_column_attack_metrics
from aegisguard_q.qgl_attack import extract_heavy_walsh_candidates


def test_v2_report_fields_and_notes():
    r = analyze_noise_function(4, nf.bent_inner_product(4))
    assert r.mutual_information == 0.0
    assert r.stabilizer_size == 16
    assert "Corollary 4" in r.notes[0]


def test_random_anf_uses_unique_monomials():
    g = nf.random_anf(2, 1, 100, seed=1)
    assert [g(a) for a in range(4)] == [0, 1, 1, 0]


def test_keyed_profiles_are_invariant_when_shifted():
    keys = list(range(8))
    fn = lambda s: nf.keyed_tribes_dlpn(3, s, width=1)
    assert key_invariance_check(3, fn, keys)
    summary = profile_keyed_family("tribes", 3, fn, keys)
    assert summary.num_keys == 8


def test_qgl_heavy_candidates():
    candidates = extract_heavy_walsh_candidates(3, nf.affine(3, 5), 0.99)
    assert candidates == [(5, 1.0)]


def test_hbplus_traces_out_b():
    result = hbplus_entangled_b_leakage(2, 1, 0, lambda a, b: 0)
    assert math.isclose(sum(result["reduced_distribution"]), 1.0)
    assert result["mode_match_x"]


def test_hbsharp_column_metrics():
    result = hbsharp_column_attack_metrics(2, 2, [nf.affine(2), nf.bent_inner_product(2)])
    assert result["fully_identifiable_columns"] == 1
    assert result["total_quantum_queries"] is None


def test_nisq_boundaries():
    g = nf.affine(3)
    assert noisy_spectral_distribution(3, g, 1.0) == [1 / 8] * 8
    assert noisy_channel_metrics(3, g, 1.0)["MI_noisy"] == 0.0
    assert noisy_channel_metrics(3, g, 0.0)["gamma_eff"] == 1.0

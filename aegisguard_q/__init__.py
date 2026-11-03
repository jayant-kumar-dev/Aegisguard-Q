"""AegisGuard-Q: quantum-leakage static analysis for deterministic-LPN noise functions."""
from .core import (
    analyze_noise_function,
    LeakageReport,
    LeakageClass,
    walsh_spectrum,
    fast_walsh_hadamard,
)
from .information import (
    spectral_distribution,
    shannon_entropy,
    mutual_information,
    translation_stabilizer,
    spectral_ambiguity_index,
    probability_gap,
    empirical_mode_bound,
    max_normalized_walsh,
)
from . import noise_functions
from .report import to_json, to_markdown
from .keyed_dlpn import KeyedFamilySummary, profile_keyed_family, key_invariance_check
from .qgl_attack import extract_heavy_walsh_candidates, keyed_secret_intersection_attack
from .protocols import hbplus_entangled_b_leakage, hbsharp_column_attack_metrics
from .nisq_channel import noisy_spectral_distribution, noisy_channel_metrics

__version__ = "3.0.0"
__all__ = [
    "analyze_noise_function", "LeakageReport", "LeakageClass",
    "walsh_spectrum", "fast_walsh_hadamard", "noise_functions",
    "to_json", "to_markdown",
    "spectral_distribution", "shannon_entropy", "mutual_information",
    "translation_stabilizer", "spectral_ambiguity_index",
    "probability_gap", "empirical_mode_bound", "max_normalized_walsh",
    "KeyedFamilySummary", "profile_keyed_family", "key_invariance_check",
    "extract_heavy_walsh_candidates", "keyed_secret_intersection_attack",
    "hbplus_entangled_b_leakage", "hbsharp_column_attack_metrics",
    "noisy_spectral_distribution", "noisy_channel_metrics",
]

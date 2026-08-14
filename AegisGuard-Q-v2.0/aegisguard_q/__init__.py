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

__version__ = "2.0.0"
__all__ = [
    "analyze_noise_function", "LeakageReport", "LeakageClass",
    "walsh_spectrum", "fast_walsh_hadamard", "noise_functions",
    "to_json", "to_markdown",
    "spectral_distribution", "shannon_entropy", "mutual_information",
    "translation_stabilizer", "spectral_ambiguity_index",
    "probability_gap", "empirical_mode_bound", "max_normalized_walsh",
]

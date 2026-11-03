"""Exact spectral profiling helpers for keyed deterministic-LPN families."""

from dataclasses import dataclass
from typing import Callable, List

from .core import analyze_noise_function
from .information import spectral_distribution


@dataclass
class KeyedFamilySummary:
    family_name: str
    n: int
    num_keys: int
    mean_tau: float
    mean_mi: float
    min_mi: float
    max_mi: float
    unique_mode_fraction: float
    trivial_stabilizer_fraction: float
    weak_key_count: int


def profile_keyed_family(
    family_name: str,
    n: int,
    key_fn: Callable[[int], Callable[[int], int]],
    key_space: List[int],
) -> KeyedFamilySummary:
    reports = [analyze_noise_function(n, key_fn(s)) for s in key_space]
    if not reports:
        return KeyedFamilySummary(family_name, n, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
    return KeyedFamilySummary(
        family_name=family_name,
        n=n,
        num_keys=len(reports),
        mean_tau=sum(r.tau for r in reports) / len(reports),
        mean_mi=sum(r.mutual_information for r in reports) / len(reports),
        min_mi=min(r.mutual_information for r in reports),
        max_mi=max(r.mutual_information for r in reports),
        unique_mode_fraction=sum(r.sai == 1 for r in reports) / len(reports),
        trivial_stabilizer_fraction=sum(r.stabilizer_size == 1 for r in reports) / len(reports),
        weak_key_count=sum(r.completeness_bound * 2.0 >= 0.5 for r in reports),
    )


def key_invariance_check(
    n: int,
    key_fn: Callable[[int], Callable[[int], int]],
    key_space: List[int],
) -> bool:
    spectra = [
        sorted(spectral_distribution(n, key_fn(s)))
        for s in key_space
    ]
    return all(s == spectra[0] for s in spectra[1:]) if spectra else True

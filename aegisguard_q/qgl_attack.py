"""Exact recursive heavy-Walsh candidate extraction and intersection attacks."""

from typing import Callable, List, Tuple

from .core import walsh_spectrum


def extract_heavy_walsh_candidates(
    n: int, h_oracle: Callable[[int], int], gamma_threshold: float
) -> List[Tuple[int, float]]:
    if gamma_threshold < 0:
        raise ValueError("gamma_threshold must be non-negative")
    W = walsh_spectrum(n, h_oracle)
    dim = 1 << n
    threshold = gamma_threshold * gamma_threshold
    result = []
    prefixes = [0]
    for k in range(1, n + 1):
        next_prefixes = []
        remaining = n - k
        for prefix in prefixes:
            for bit in (0, 1):
                child = (prefix << 1) | bit
                weight = sum((W[(child << remaining) | suffix] / dim) ** 2
                             for suffix in range(1 << remaining))
                if weight >= threshold:
                    next_prefixes.append(child)
        prefixes = next_prefixes
    for w in prefixes:
        p = (W[w] / dim) ** 2
        if abs(W[w]) / dim >= gamma_threshold:
            result.append((w, p))
    return result


def keyed_secret_intersection_attack(
    n: int,
    secret_x: int,
    key_fn: Callable[[int], Callable[[int], int]],
    rotated_keys: List[int],
    top_k: int = 4,
) -> List[int]:
    candidates = set(range(1 << n))
    for key in rotated_keys:
        noise = key_fn(key)
        h = lambda a, noise=noise, x=secret_x: (
            (a & x).bit_count() & 1
        ) ^ noise(a)
        peaks = sorted(
            extract_heavy_walsh_candidates(n, h, 0.0),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        candidates &= {w ^ u for w, _ in peaks}
    return sorted(candidates)

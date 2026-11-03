"""Protocol-level physical leakage models."""

from typing import Callable, List

from .core import analyze_noise_function
from .information import spectral_distribution, shannon_entropy


def hbplus_entangled_b_leakage(
    n: int, x: int, y: int, g_2n: Callable[[int, int], int]
) -> dict:
    dim = 1 << n
    reduced = [0.0] * dim
    for b in range(dim):
        g_b = lambda a, b=b: ((b & y).bit_count() & 1) ^ g_2n(a, b)
        p = spectral_distribution(n, g_b)
        for w in range(dim):
            reduced[w] += p[w ^ x] / dim
    return {
        "reduced_distribution": reduced,
        "MI_reduced": max(0.0, n - shannon_entropy(reduced)),
        "mode_match_x": max(range(dim), key=lambda w: reduced[w]) == x,
    }


def hbsharp_column_attack_metrics(
    n_x: int,
    m: int,
    col_noise_fns: List[Callable[[int], int]],
    epsilon: float = 0.05,
) -> dict:
    columns = []
    for g in col_noise_fns[:m]:
        r = analyze_noise_function(n_x, g, epsilon=epsilon)
        columns.append({
            "MI": r.mutual_information,
            "SAI": r.sai,
            "stabilizer_size": r.stabilizer_size,
            "query_complexity": r.query_complexity,
        })
    all_unique = all(c["SAI"] == 1 for c in columns)
    total = sum(c["query_complexity"] or 0 for c in columns) if all_unique else None
    return {
        "columns": columns,
        "MI": [c["MI"] for c in columns],
        "SAI": [c["SAI"] for c in columns],
        "stabilizer_size": [c["stabilizer_size"] for c in columns],
        "query_complexity": [c["query_complexity"] for c in columns],
        "total_quantum_queries": total,
        "fully_identifiable_columns": sum(c["stabilizer_size"] == 1 for c in columns),
    }

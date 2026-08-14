"""
aegisguard_q.cli
===============

Command-line interface. Analyze a built-in noise-function family and emit a
JSON or markdown leakage report.

Examples:
    python -m aegisguard_q.cli --family bent --n 8 --format markdown
    python -m aegisguard_q.cli --family anf --n 10 --degree 3 --terms 8 --format json
"""

from __future__ import annotations

import argparse
import sys

from .core import analyze_noise_function
from . import noise_functions as nf
from .report import to_json, to_markdown


def _build_g(args):
    if args.family == "affine":
        return nf.affine(args.n, s=args.s, c=args.c)
    if args.family == "linear":
        return nf.linear(args.n, s=args.s if args.s else 1)
    if args.family == "bent":
        return nf.bent_inner_product(args.n)
    if args.family == "anf":
        return nf.random_anf(args.n, degree=args.degree,
                             num_terms=args.terms, seed=args.seed)
    raise ValueError(f"unknown family {args.family}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aegisguard-q",
                                description="Quantum-leakage analysis of "
                                            "deterministic-LPN noise functions.")
    p.add_argument("--family", required=True,
                   choices=["affine", "linear", "bent", "anf"])
    p.add_argument("--n", type=int, required=True, help="register size")
    p.add_argument("--degree", type=int, default=2, help="anf monomial degree")
    p.add_argument("--terms", type=int, default=4, help="anf number of terms")
    p.add_argument("--s", type=int, default=0, help="linear/affine mask s")
    p.add_argument("--c", type=int, default=0, help="affine constant c")
    p.add_argument("--seed", type=int, default=0, help="anf random seed")
    p.add_argument("--epsilon", type=float, default=0.05,
                   help="target failure prob for query-complexity estimate")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = p.parse_args(argv)

    try:
        g = _build_g(args)
        report = analyze_noise_function(args.n, g, epsilon=args.epsilon)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(to_json(report) if args.format == "json" else to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

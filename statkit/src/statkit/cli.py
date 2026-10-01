"""Command line: compare one numeric column across two CSV files."""
import argparse
import csv
import json
import sys

from . import bootstrap_ci, hedges_g, permutation_test


def _read_column(path, column):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if column not in (reader.fieldnames or []):
            raise SystemExit(f"column '{column}' not found in {path}")
        return [float(row[column]) for row in reader if row[column] != ""]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="statkit", description="Compare two groups.")
    ap.add_argument("group_a")
    ap.add_argument("group_b")
    ap.add_argument("--column", required=True)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed (default 0, for reproducibility)")
    ap.add_argument("--n-boot", type=int, default=10_000)
    args = ap.parse_args(argv)

    a = _read_column(args.group_a, args.column)
    b = _read_column(args.group_b, args.column)
    diff, p = permutation_test(a, b, seed=args.seed)
    result = {
        "n_a": len(a), "n_b": len(b),
        "mean_difference": diff,
        "permutation_p": p,
        "hedges_g": hedges_g(a, b),
        "ci95_a": bootstrap_ci(a, n_boot=args.n_boot, seed=args.seed)[1:],
        "ci95_b": bootstrap_ci(b, n_boot=args.n_boot, seed=args.seed)[1:],
        "seed": args.seed,
    }
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

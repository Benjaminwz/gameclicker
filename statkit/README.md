# statkit

Small, dependency-light (NumPy only) statistics helpers for reproducible research.

- Effect sizes: `cohens_d`, `hedges_g`
- Percentile bootstrap CI: `bootstrap_ci`
- Two-sample permutation test (add-one corrected p-value): `permutation_test`
- Multiple-comparison correction: `bonferroni`, `holm`, `benjamini_hochberg`
- CLI to compare a column across two CSV files

## Install
```
cd statkit
pip install -e ".[dev]"
```

## Use
```python
from statkit import hedges_g, permutation_test, bootstrap_ci

diff, p = permutation_test(a, b, seed=42)
g = hedges_g(a, b)
est, lo, hi = bootstrap_ci(a, seed=42)
```
```
statkit a.csv b.csv --column score --seed 42
```
All randomised functions take a `seed`; the CLI defaults to `--seed 0` so results are reproducible.

## Test
```
pytest && ruff check .
```

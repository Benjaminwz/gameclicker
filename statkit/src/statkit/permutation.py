"""Two-sample permutation test."""
import numpy as np

from ._util import as_sample


def permutation_test(a, b, n_perm=10_000, seed=None):
    """Two-sided permutation test for a difference in means.

    Uses the add-one correction, so the returned p-value is never exactly 0:
    ``p = (1 + #{|T*| >= |T|}) / (1 + n_perm)``.
    Returns ``(observed_difference, p_value)``.
    """
    if n_perm < 100:
        raise ValueError("n_perm must be at least 100")
    a, b = as_sample(a, "a", 1), as_sample(b, "b", 1)
    rng = np.random.default_rng(seed)
    pooled = np.concatenate([a, b])
    observed = a.mean() - b.mean()
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        diff = pooled[: a.size].mean() - pooled[a.size:].mean()
        hits += abs(diff) >= abs(observed) - 1e-12
    return float(observed), float((1 + hits) / (1 + n_perm))

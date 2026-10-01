"""Percentile bootstrap confidence intervals."""
import numpy as np

from ._util import as_sample


def bootstrap_ci(data, statistic=np.mean, n_boot=10_000, alpha=0.05, seed=None):
    """Percentile bootstrap CI for ``statistic`` of one sample.

    Returns ``(estimate, lower, upper)``. Pass ``seed`` for reproducible results.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if n_boot < 100:
        raise ValueError("n_boot must be at least 100")
    x = as_sample(data, "data")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    stats = np.array([statistic(x[row]) for row in idx])
    lower, upper = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return float(statistic(x)), float(lower), float(upper)
